import logging
from src.ingest import fetch_play_store_reviews

# Configure logging to output details
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

if __name__ == "__main__":
    # Testing for preceding week (2026-W24)
    iso_week = "2026-W24"
    print(f"--- Running Ingestion Test for {iso_week} ---")
    try:
        reviews_list = fetch_play_store_reviews(iso_week, use_cache=False)
        print(f"\n[SUCCESS] Fetch Completed! Total Reviews Found: {len(reviews_list)}")
        if reviews_list:
            print("\nSample Ingested Review (PII Scrubbed):")
            safe_sample = str(reviews_list[0]).encode('ascii', errors='replace').decode('ascii')
            print(safe_sample)
    except Exception as e:
        print(f"\n[FAILURE] Test Failed with Error: {e}")
