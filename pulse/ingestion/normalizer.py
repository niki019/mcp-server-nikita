import re

# Regex for emojis and miscellaneous symbols
EMOJI_REGEX = re.compile(r'[\U00010000-\U0010ffff\u2600-\u27bf]')

def remove_emojis(text: str) -> str:
    """Removes all emojis and miscellaneous symbols from the text."""
    if not text:
        return ""
    return EMOJI_REGEX.sub("", text)

def normalize_text(text: str, min_words: int = 8) -> str:
    """
    Applies normalization rules:
    - Removes emojis
    - Normalizes whitespace
    - Discards review if under the min_words threshold
    """
    if not text:
        return ""
    
    cleaned = remove_emojis(text)
    # Normalize whitespace
    cleaned = " ".join(cleaned.split())
    
    # Word count filter
    if len(cleaned.split()) < min_words:
        return ""
        
    return cleaned
