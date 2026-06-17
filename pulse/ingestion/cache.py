import os
import json
import logging
from pulse.config import CACHE_DIR

logger = logging.getLogger("pulse-cache")

def get_raw_cache_path(product: str, iso_week: str) -> str:
    return os.path.join(CACHE_DIR, f"raw_reviews_{iso_week}.json")

def get_normalized_cache_path(product: str, iso_week: str) -> str:
    return os.path.join(CACHE_DIR, f"normalized_reviews_{iso_week}.json")

def load_normalized_cache(product: str, iso_week: str) -> list[dict]:
    path = get_normalized_cache_path(product, iso_week)
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading normalized cache from {path}: {e}")
    return []

def save_raw_cache(product: str, iso_week: str, raw_reviews: list[dict]):
    path = get_raw_cache_path(product, iso_week)
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(raw_reviews, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved raw cache to {path}")
    except Exception as e:
        logger.error(f"Failed to write raw cache to {path}: {e}")

def save_normalized_cache(product: str, iso_week: str, normalized_reviews: list[dict]):
    path = get_normalized_cache_path(product, iso_week)
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(normalized_reviews, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved normalized cache to {path}")
    except Exception as e:
        logger.error(f"Failed to write normalized cache to {path}: {e}")
