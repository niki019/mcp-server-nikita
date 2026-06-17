import os
import json
import logging
import datetime
from google_play_scraper import reviews, Sort
from src.config import APP_PACKAGE_ID, DEFAULT_COUNTRY, DEFAULT_LANGUAGE, CACHE_DIR
from src.ingest import scrub_pii, remove_emojis

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("cache-regenerator")

def get_last_n_iso_weeks(n=10):
    """Returns a list of the last N completed ISO week strings (e.g. YYYY-Www)."""
    weeks = []
    today = datetime.date.today()
    # Go back to the Monday of the current week, then back 1 week for the last completed week
    current_monday = today - datetime.timedelta(days=today.weekday())
    last_completed_monday = current_monday - datetime.timedelta(days=7)
    
    for i in range(n):
        monday = last_completed_monday - datetime.timedelta(weeks=i)
        year, week, weekday = monday.isocalendar()
        weeks.append(f"{year}-W{week:02d}")
    return weeks

def regenerate_cache(num_weeks=10):
    # 1. Determine target weeks and the oldest date boundary
    target_weeks = get_last_n_iso_weeks(num_weeks)
    logger.info(f"Target weeks to cache: {target_weeks}")
    
    # Oldest week start date (Monday of the oldest target week)
    oldest_week = target_weeks[-1]
    # Strptime requires weekday suffix (1 = Monday)
    oldest_start_date = datetime.datetime.strptime(f"{oldest_week}-1", "%G-W%V-%u")
    oldest_dt = oldest_week_start = oldest_start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Newest week end date (Sunday of the latest target week)
    newest_week = target_weeks[0]
    newest_start_date = datetime.datetime.strptime(f"{newest_week}-1", "%G-W%V-%u")
    newest_end_dt = newest_start_date + datetime.timedelta(days=7)
    
    logger.info(f"Ingesting reviews from {oldest_dt} up to {newest_end_dt} (UTC)")
    
    # Dictionary to group raw reviews by ISO week
    weeks_raw_data = {week: [] for week in target_weeks}
    
    # 2. Scrape reviews in a single continuous pass
    continuation_token = None
    finished = False
    page = 0
    max_pages = 150  # High page limit to ensure we reach 10 weeks ago
    total_scraped = 0
    
    while not finished and page < max_pages:
        page += 1
        logger.info(f"Scraping page {page} from Play Store...")
        try:
            batch, continuation_token = reviews(
                APP_PACKAGE_ID,
                lang=DEFAULT_LANGUAGE,
                country=DEFAULT_COUNTRY,
                sort=Sort.NEWEST,
                count=100,
                continuation_token=continuation_token
            )
        except Exception as e:
            logger.error(f"Scraper error: {e}")
            break
            
        if not batch:
            logger.info("No more reviews returned by scraper.")
            break
            
        for r in batch:
            review_date = r.get('at')
            if not review_date:
                continue
                
            # Stop condition: reached reviews older than the oldest week's start date
            if review_date < oldest_dt:
                logger.info(f"Reached review dated {review_date}, which is older than {oldest_dt}. Stopping scrape.")
                finished = True
                break
                
            total_scraped += 1
            
            # Map review to its ISO week
            year, week, weekday = review_date.isocalendar()
            iso_week = f"{year}-W{week:02d}"
            
            if iso_week in weeks_raw_data:
                # Convert datetime objects to strings for clean JSON serialization
                raw_review = r.copy()
                if isinstance(raw_review.get('at'), datetime.datetime):
                    raw_review['at'] = raw_review['at'].isoformat()
                if isinstance(raw_review.get('repliedAt'), datetime.datetime):
                    raw_review['repliedAt'] = raw_review['repliedAt'].isoformat()
                weeks_raw_data[iso_week].append(raw_review)
                
        if not continuation_token:
            break
            
    logger.info(f"Scrape completed. Total parsed reviews: {total_scraped}")
    
    # Helper to serialize datetimes
    datetime_serializer = lambda o: o.isoformat() if isinstance(o, (datetime.datetime, datetime.date)) else str(o)
    
    # 3. Process, normalize, and save cache for each week
    for week in target_weeks:
        raw_reviews = weeks_raw_data[week]
        raw_cache_file = os.path.join(CACHE_DIR, f"raw_reviews_{week}.json")
        normalized_cache_file = os.path.join(CACHE_DIR, f"normalized_reviews_{week}.json")
        
        # Save Raw Reviews Cache
        try:
            with open(raw_cache_file, 'w', encoding='utf-8') as f:
                json.dump(raw_reviews, f, indent=2, ensure_ascii=False, default=datetime_serializer)
        except Exception as e:
            logger.error(f"Failed to save raw cache for {week}: {e}")
            
        # Apply Normalization
        normalized_reviews = []
        for r in raw_reviews:
            content = r.get("content", "")
            content = scrub_pii(content)
            content = remove_emojis(content)
            content = " ".join(content.split())
            
            if len(content.split()) < 8:
                continue
                
            normalized_review = {
                "content": content,
                "score": r.get("score"),
                "thumbsUpCount": r.get("thumbsUpCount")
            }
            normalized_reviews.append(normalized_review)
            
        # Save Normalized Reviews Cache
        try:
            with open(normalized_cache_file, 'w', encoding='utf-8') as f:
                json.dump(normalized_reviews, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save normalized cache for {week}: {e}")
            
        # Print results safely for Windows terminal
        logger.info(f"Week {week}: Saved {len(raw_reviews)} raw reviews, {len(normalized_reviews)} normalized reviews.")

if __name__ == "__main__":
    print("--- Starting 10-Week Cache Regeneration ---")
    regenerate_cache(num_weeks=10)
    print("--- Cache Regeneration Finished ---")
