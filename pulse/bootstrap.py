import os
import json
import logging

logger = logging.getLogger("pulse-bootstrap")
logging.basicConfig(level=logging.INFO)

def bootstrap_secrets():
    """
    Parses Google Client credentials and token JSON stringified variables from
    the environment and writes them to their expected files locally on start.
    This ensures we don't commit secrets to the Git repository.
    """
    logger.info("Checking environment for Google Workspace API secrets...")
    
    # 1. Write credentials.json
    creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if creds_json:
        creds_path = os.path.join("mcp_server", "credentials.json")
        os.makedirs(os.path.dirname(creds_path), exist_ok=True)
        try:
            # Validate JSON format before writing
            data = json.loads(creds_json)
            with open(creds_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            logger.info(f"Successfully bootstrapped Google credentials to {creds_path}")
        except json.JSONDecodeError as e:
            logger.error(f"GOOGLE_CREDENTIALS_JSON contains invalid JSON: {e}")
            
    # 2. Write token.json
    token_json = os.getenv("GOOGLE_TOKEN_JSON")
    if token_json:
        token_path = os.path.join("mcp_server", "token.json")
        os.makedirs(os.path.dirname(token_path), exist_ok=True)
        try:
            # Validate JSON format before writing
            data = json.loads(token_json)
            with open(token_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            logger.info(f"Successfully bootstrapped Google OAuth token to {token_path}")
        except json.JSONDecodeError as e:
            logger.error(f"GOOGLE_TOKEN_JSON contains invalid JSON: {e}")

if __name__ == "__main__":
    bootstrap_secrets()
