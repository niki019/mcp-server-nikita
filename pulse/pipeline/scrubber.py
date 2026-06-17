import re

EMAIL_REGEX = re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+')
PHONE_REGEX = re.compile(r'\b\+?\d{1,4}?[-.\s]?\(?\d{1,3}?\)?[-.\s]?\d{3}[-.\s]?\d{3,4}\b|\b[6-9]\d{9}\b')
ID_REGEX = re.compile(r'\b[A-Z]{5}\d{4}[A-Z]\b|\b\d{12}\b|\b\d{4}\s\d{4}\s\d{4}\b|\b\d{10,11}\b')

def scrub_pii(text: str) -> str:
    """
    Scrubs PII from the review text:
    - Emails -> [EMAIL]
    - Phones -> [PHONE]
    - PAN/Aadhaar/long numeric sequences -> [ID]
    - URL path/query parameters with tokens -> Redacted
    """
    if not text:
        return ""
        
    text = EMAIL_REGEX.sub("[EMAIL]", text)
    text = PHONE_REGEX.sub("[PHONE]", text)
    text = ID_REGEX.sub("[ID]", text)
    
    # Redact path/query of URLs with tokens
    urls = re.findall(r'https?://[^\s]+', text)
    for url in urls:
        if any(k in url.lower() for k in ['token', 'key', 'pass', 'auth', 'code', 'session', 'id']):
            match = re.match(r'(https?://[a-zA-Z0-9.-]+)(/[^\s]*)?', url)
            if match:
                domain = match.group(1)
                text = text.replace(url, f"{domain}/[TOKEN_REDACTED]")
                
    return text
