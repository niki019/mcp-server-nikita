import os
import sys
import logging

# Add parent directory to sys.path to enable absolute imports of mcp_server
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp.server.fastmcp import FastMCP
from mcp_server.google_client import GoogleWorkspaceClient

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("workspace-mcp-server")

# Initialize FastMCP server
mcp = FastMCP("Workspace-Server")

# Lazy load Google Workspace client to prevent startup errors if token is missing
google_client = None

def get_google_client():
    global google_client
    if google_client is None:
        logger.info("Initializing Google Workspace Client...")
        google_client = GoogleWorkspaceClient()
    return google_client

@mcp.tool()
def append_to_doc(doc_id: str, title: str, markdown_content: str) -> str:
    """
    Appends a new dated section with formatting (markdown) to a Google Doc.
    
    Args:
        doc_id: The ID of the target Google Document (found in the document URL).
        title: The heading for this week's section (e.g. "Groww - Weekly Review Pulse [2026-W25]").
        markdown_content: The markdown formatted review summary content to append.
        
    Returns:
        The direct browser URL pointing to the newly added heading anchor in the Doc.
    """
    logger.info(f"Received request to append section '{title}' to Doc '{doc_id}'")
    try:
        client = get_google_client()
        anchor_url = client.append_markdown_to_doc(doc_id, title, markdown_content)
        logger.info(f"Successfully appended section. Anchor URL: {anchor_url}")
        return anchor_url
    except Exception as e:
        logger.error(f"Failed to append to Doc: {e}")
        return f"Error: {str(e)}"

@mcp.tool()
def send_gmail_teaser(recipient: str, subject: str, html_body: str) -> str:
    """
    Sends an HTML formatted teaser email to stakeholders.
    
    Args:
        recipient: The email address of the recipient.
        subject: The subject line of the email.
        html_body: The HTML content of the email containing a deep link to the Google Doc section.
        
    Returns:
        The sent Gmail message ID.
    """
    logger.info(f"Received request to send email to '{recipient}' with subject '{subject}'")
    try:
        client = get_google_client()
        message_id = client.send_gmail_message(recipient, subject, html_body)
        logger.info(f"Successfully sent email. Message ID: {message_id}")
        return message_id
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return f"Error: {str(e)}"

if __name__ == "__main__":
    # Start the FastMCP server (default runs via stdio transport)
    mcp.run()
