import logging
import datetime
from google_play_scraper import reviews, Sort
from pulse.ingestion.normalizer import normalize_text
from pulse.pipeline.scrubber import scrub_pii
from pulse.ingestion.cache import save_raw_cache, save_normalized_cache

logger = logging.getLogger("pulse-play-store-ingestion")

def parse_iso_week(iso_week_str: str):
    """Parses YYYY-Www into naive datetime start (Monday) and end (Sunday) boundaries."""
    try:
        start_date = datetime.datetime.strptime(f"{iso_week_str}-1", "%G-W%V-%u")
        start_dt = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_dt = start_dt + datetime.timedelta(days=7)
        return start_dt, end_dt
    except ValueError as e:
        raise ValueError(f"Invalid ISO week format '{iso_week_str}'. Expected: YYYY-Www") from e

def scrape_play_store_reviews(app_id: str, iso_week: str, limit: int = 5000) -> list[dict]:
    """Scrapes reviews from Google Play Store for the target week."""
    start_dt, end_dt = parse_iso_week(iso_week)
    logger.info(f"Scraping reviews for {app_id} between {start_dt} and {end_dt}")
    
    raw_reviews = []
    continuation_token = None
    finished = False
    page = 0
    max_pages = limit // 100
    
    while not finished and page < max_pages:
        page += 1
        try:
            batch, continuation_token = reviews(
                app_id,
                lang='en',
                country='in',
                sort=Sort.NEWEST,
                count=100,
                continuation_token=continuation_token
            )
        except Exception as e:
            logger.error(f"Play Store scraper failed: {e}")
            raise e
            
        if not batch:
            break
            
        for r in batch:
            review_date = r.get('at')
            if not review_date:
                continue
                
            if review_date < start_dt:
                finished = True
                break
                
            if start_dt <= review_date < end_dt:
                # Convert datetime to string for json serialization
                r_copy = r.copy()
                if isinstance(r_copy.get('at'), datetime.datetime):
                    r_copy['at'] = r_copy['at'].isoformat()
                if isinstance(r_copy.get('repliedAt'), datetime.datetime):
                    r_copy['repliedAt'] = r_copy['repliedAt'].isoformat()
                raw_reviews.append(r_copy)
                
        if not continuation_token:
            break
            
    return raw_reviews

def fetch_reviews(product_name: str, product_config: dict, iso_week: str) -> list[dict]:
    """
    Scrapes Play Store reviews, applies normalization/scrubbing, and caches both raw & normalized data.
    """
    app_id = product_config.get("play_store", {}).get("app_id", "com.nextbillion.groww")
    ingest_settings = product_config.get("ingestion", {})
    min_words = ingest_settings.get("min_words", 8)
    
    # 1. Scrape raw reviews
    raw_reviews = scrape_play_store_reviews(app_id, iso_week, limit=ingest_settings.get("max_reviews", 5000))
    logger.info(f"Scraped {len(raw_reviews)} raw reviews.")
    
    # 2. Save raw cache
    save_raw_cache(product_name, iso_week, raw_reviews)
    
    # 3. Normalize & scrub PII
    normalized_reviews = []
    for r in raw_reviews:
        content = r.get("content", "")
        # Apply normalization rules
        cleaned_content = normalize_text(content, min_words)
        if not cleaned_content:
            continue
            
        # Scrub PII
        scrubbed_content = scrub_pii(cleaned_content)
        
        normalized_reviews.append({
            "content": scrubbed_content,
            "score": r.get("score"),
            "thumbsUpCount": r.get("thumbsUpCount")
        })
        
    # 4. Save normalized cache
    save_normalized_cache(product_name, iso_week, normalized_reviews)
    
    return normalized_reviews
