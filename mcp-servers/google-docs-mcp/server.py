import os
import sys
import logging
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from mcp.server.fastmcp import FastMCP

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("google-docs-mcp")

mcp = FastMCP("Google-Docs-MCP")

# Scope for Google Docs
SCOPES = ['https://www.googleapis.com/auth/documents']

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
    return build('docs', 'v1', credentials=creds)

@mcp.tool()
def find_section_by_anchor(document_id: str, anchor: str) -> dict:
    """
    Checks if a section with the given anchor heading already exists in the document.
    
    Args:
        document_id: The ID of the target Google Doc.
        anchor: The expected text of the Heading 2 (e.g. "Groww - Weekly Review Pulse - 2026-W23").
        
    Returns:
        A dictionary with keys 'found', 'heading_id', and 'url_fragment'.
    """
    logger.info(f"Looking for section anchor '{anchor}' in document '{document_id}'...")
    try:
        service = get_service()
        doc = service.documents().get(documentId=document_id).execute()
        body_elements = doc.get('body', {}).get('content', [])
        
        for element in body_elements:
            paragraph = element.get('paragraph')
            if paragraph:
                style = paragraph.get('paragraphStyle', {})
                if style.get('namedStyleType') == 'HEADING_2':
                    raw_text = "".join([run.get('textRun', {}).get('content', '') 
                                       for run in paragraph.get('elements', [])]).strip()
                    if anchor.lower() in raw_text.lower() or raw_text.lower() in anchor.lower():
                        heading_id = style.get('headingId')
                        logger.info(f"Found existing anchor heading with ID: h.{heading_id}")
                        return {
                            "found": True,
                            "heading_id": heading_id,
                            "url_fragment": f"#heading=h.{heading_id}"
                        }
        logger.info("Section anchor not found.")
        return {"found": False}
    except Exception as e:
        logger.error(f"Error in find_section_by_anchor: {e}")
        return {"found": False, "error": str(e)}

@mcp.tool()
def get_document_url(document_id: str, heading_id: str = None) -> dict:
    """
    Resolves the shareable edit URL for a document, optionally deep-linking to a specific heading ID.
    """
    url = f"https://docs.google.com/document/d/{document_id}/edit"
    if heading_id:
        url += f"#heading=h.{heading_id}"
    return {"url": url}

@mcp.tool()
def append_section(document_id: str, anchor: str, blocks: list[dict], insert_at_end: bool = True) -> dict:
    """
    Appends a structured report section with formatting to a Google Doc.
    
    Args:
        document_id: The ID of the target Google Doc.
        anchor: The Heading 2 title for the section (e.g. "Groww - Weekly Review Pulse - 2026-W23").
        blocks: A list of dict blocks where each block has keys 'type' ('heading_2', 'heading_3', 'paragraph', 'bullet', 'quote') and 'text'.
        insert_at_end: If true, appends at the end of the document.
        
    Returns:
        A dictionary with 'heading_id', 'revision_id', and 'url'.
    """
    logger.info(f"Appending section '{anchor}' to document '{document_id}'...")
    try:
        service = get_service()
        doc = service.documents().get(documentId=document_id).execute()
        body = doc.get('body', {})
        content_list = body.get('content', [])
        
        # Determine insertion index
        end_index = content_list[-1].get('endIndex', 1) - 1
        if end_index < 1:
            end_index = 1
            
        full_text = ""
        requests = []
        
        # 1. Start with the main dated section heading
        dated_title = f"\n\n{anchor}\n"
        full_text += dated_title
        title_start = end_index + 2
        title_end = end_index + len(dated_title)
        
        requests.append({
            'updateParagraphStyle': {
                'range': {'startIndex': title_start, 'endIndex': title_end},
                'paragraphStyle': {'namedStyleType': 'HEADING_2'},
                'fields': 'namedStyleType'
            }
        })
        
        current_idx = end_index + len(dated_title)
        
        # 2. Add each structured block
        for block in blocks:
            b_type = block.get('type')
            b_text = block.get('text', '').strip()
            if not b_text:
                continue
                
            text_to_append = b_text + "\n"
            full_text += text_to_append
            start = current_idx
            end = current_idx + len(text_to_append)
            
            if b_type == 'heading_2':
                requests.append({
                    'updateParagraphStyle': {
                        'range': {'startIndex': start, 'endIndex': end},
                        'paragraphStyle': {'namedStyleType': 'HEADING_2'},
                        'fields': 'namedStyleType'
                    }
                })
            elif b_type == 'heading_3':
                requests.append({
                    'updateParagraphStyle': {
                        'range': {'startIndex': start, 'endIndex': end},
                        'paragraphStyle': {'namedStyleType': 'HEADING_3'},
                        'fields': 'namedStyleType'
                    }
                })
            elif b_type == 'bullet':
                requests.append({
                    'createParagraphBullets': {
                        'range': {'startIndex': start, 'endIndex': end},
                        'bulletPreset': 'BULLET_DISC_CIRCLE_SQUARE'
                    }
                })
            elif b_type == 'quote':
                requests.append({
                    'updateTextStyle': {
                        'range': {'startIndex': start, 'endIndex': end},
                        'textStyle': {
                            'italic': True,
                            'foregroundColor': {'color': {'rgbColor': {'red': 0.4, 'green': 0.4, 'blue': 0.4}}}
                        },
                        'fields': 'italic,foregroundColor'
                    }
                })
            else: # paragraph
                requests.append({
                    'updateParagraphStyle': {
                        'range': {'startIndex': start, 'endIndex': end},
                        'paragraphStyle': {'namedStyleType': 'NORMAL_TEXT'},
                        'fields': 'namedStyleType'
                    }
                })
                
            current_idx = end
            
        # 3. Add the initial insert text request
        insert_request = {
            'insertText': {
                'location': {'index': end_index},
                'text': full_text
            }
        }
        requests.insert(0, insert_request)
        
        # 4. Perform the updates
        res = service.documents().batchUpdate(
            documentId=document_id,
            body={'requests': requests}
        ).execute()
        
        # 5. Retrieve headingId for the new section
        doc = service.documents().get(documentId=document_id).execute()
        elements = doc.get('body', {}).get('content', [])
        heading_id = None
        for element in elements:
            paragraph = element.get('paragraph')
            if paragraph:
                style = paragraph.get('paragraphStyle', {})
                if style.get('namedStyleType') == 'HEADING_2':
                    raw_text = "".join([run.get('textRun', {}).get('content', '') 
                                       for run in paragraph.get('elements', [])]).strip()
                    if anchor in raw_text:
                        heading_id = style.get('headingId')
                        break
                        
        url = f"https://docs.google.com/document/d/{document_id}/edit"
        if heading_id:
            url += f"#heading=h.{heading_id}"
            
        return {
            "heading_id": heading_id,
            "revision_id": res.get("writeControl", {}).get("requiredRevisionId", ""),
            "url": url
        }
    except Exception as e:
        logger.error(f"Error in append_section: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    mcp.run()
