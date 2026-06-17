import os
import re
import base64
import sqlite3
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from mcp.server.fastmcp import FastMCP

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gmail-mcp")

mcp = FastMCP("Gmail-MCP")

# Scope for Gmail (allows compose and send)
SCOPES = ['https://www.googleapis.com/auth/gmail.compose', 'https://www.googleapis.com/auth/gmail.send']

# Database path for idempotency
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gmail_idempotency.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS idempotency_ledger (
            idempotency_key TEXT PRIMARY KEY,
            external_id TEXT,
            channel_type TEXT, -- 'draft' or 'send'
            sent_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

# Initialize DB on load
init_db()

def get_credentials():
    """Authenticate and return credentials."""
    creds_path = os.getenv("GOOGLE_CREDENTIALS_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "credentials.json"))
    token_path = os.getenv("GOOGLE_TOKEN_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "token.json"))
    
    # Fallback to shared location in mcp_server if they don't exist here yet
    parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    shared_creds = os.path.join(parent_dir, "mcp_server", "credentials.json")
    shared_token = os.path.join(parent_dir, "mcp_server", "token.json")
    
    if not os.path.exists(creds_path) and os.path.exists(shared_creds):
        creds_path = shared_creds
    if not os.path.exists(token_path) and os.path.exists(shared_token):
        token_path = shared_token

    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(creds_path):
                raise FileNotFoundError(f"Credentials file not found at {creds_path}")
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0)
            
        with open(token_path, 'w') as token_file:
            token_file.write(creds.to_json())
            
    return creds

def get_service():
    creds = get_credentials()
    return build('gmail', 'v1', credentials=creds)

@mcp.tool()
def check_idempotency(idempotency_key: str) -> dict:
    """
    Checks the local idempotency ledger to see if this key has already been sent/created.
    """
    logger.info(f"Checking idempotency for key: {idempotency_key}")
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT external_id, channel_type FROM idempotency_ledger WHERE idempotency_key = ?", (idempotency_key,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            logger.info(f"Key found: external_id={row[0]}, type={row[1]}")
            return {
                "already_sent": True,
                "external_id": row[0],
                "channel_type": row[1]
            }
        logger.info("Key not found in ledger.")
        return {"already_sent": False}
    except Exception as e:
        logger.error(f"Error checking idempotency: {e}")
        return {"already_sent": False, "error": str(e)}

def _record_delivery(idempotency_key: str, external_id: str, channel_type: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO idempotency_ledger (idempotency_key, external_id, channel_type) VALUES (?, ?, ?)",
        (idempotency_key, external_id, channel_type)
    )
    conn.commit()
    conn.close()

def _create_raw_email(to: list[str], subject: str, html_body: str, text_body: str) -> str:
    message = MIMEMultipart('alternative')
    message['to'] = ", ".join(to)
    message['from'] = 'me'
    message['subject'] = subject
    
    part1 = MIMEText(text_body or re.sub('<[^<]+?>', '', html_body), 'plain')
    part2 = MIMEText(html_body, 'html')
    
    message.attach(part1)
    message.attach(part2)
    
    return base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')

@mcp.tool()
def create_draft(to: list[str], subject: str, html_body: str, text_body: str, idempotency_key: str) -> dict:
    """
    Creates a draft email in the user's Gmail box, keeping track of idempotency.
    """
    logger.info(f"Received request to create draft (key: {idempotency_key}) to: {to}")
    try:
        # Check idempotency first
        existing = check_idempotency(idempotency_key)
        if existing.get("already_sent"):
            logger.info(f"Duplicate draft request ignored. Returning existing draft ID: {existing.get('external_id')}")
            return {"draft_id": existing.get("external_id"), "reused": True}
            
        service = get_service()
        raw_email = _create_raw_email(to, subject, html_body, text_body)
        
        draft_body = {
            'message': {
                'raw': raw_email
            }
        }
        
        res = service.users().drafts().create(userId='me', body=draft_body).execute()
        draft_id = res.get('id', '')
        
        # Record delivery
        _record_delivery(idempotency_key, draft_id, 'draft')
        logger.info(f"Draft created successfully. ID: {draft_id}")
        
        return {"draft_id": draft_id, "reused": False}
    except Exception as e:
        logger.error(f"Error creating draft: {e}")
        return {"error": str(e)}

@mcp.tool()
def send_email(to: list[str], subject: str, html_body: str, text_body: str, idempotency_key: str) -> dict:
    """
    Sends an email directly via the Gmail API, keeping track of idempotency.
    """
    logger.info(f"Received request to send email (key: {idempotency_key}) to: {to}")
    try:
        # Check idempotency first
        existing = check_idempotency(idempotency_key)
        if existing.get("already_sent"):
            logger.info(f"Duplicate email send request ignored. Returning existing message ID: {existing.get('external_id')}")
            return {"message_id": existing.get("external_id"), "reused": True}
            
        service = get_service()
        raw_email = _create_raw_email(to, subject, html_body, text_body)
        
        body = {'raw': raw_email}
        res = service.users().messages().send(userId='me', body=body).execute()
        message_id = res.get('id', '')
        
        # Record delivery
        _record_delivery(idempotency_key, message_id, 'send')
        logger.info(f"Email sent successfully. ID: {message_id}")
        
        return {"message_id": message_id, "reused": False}
    except Exception as e:
        logger.error(f"Error sending email: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    mcp.run()
