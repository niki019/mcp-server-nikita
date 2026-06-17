import logging
from src.ingest import fetch_play_store_reviews
from src.analyze import ReviewClusterer

# Configure logging to console
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

if __name__ == "__main__":
    iso_week = "2026-W24"
    print(f"--- Running Clustering Test for {iso_week} ---")
    
    # 1. Load normalized reviews from cache
    try:
        reviews_list = fetch_play_store_reviews(iso_week, use_cache=True)
        print(f"Successfully loaded {len(reviews_list)} normalized reviews from cache.")
    except Exception as e:
        print(f"Failed to load cached reviews: {e}")
        exit(1)
        
    if not reviews_list:
        print("No cached reviews found. Please verify cache exists.")
        exit(1)
        
    # 2. Run clustering engine
    try:
        clusterer = ReviewClusterer()
        result = clusterer.cluster_reviews(reviews_list)
        
        # 3. Print Summary of Clusters
        print("\n=== Clustering Results ===")
        print(f"Total Clusters Identified: {len(result['clusters'])}")
        print(f"Total Noise Reviews Filtered: {len(result['noise'])}")
        
        # Output sample reviews from each cluster
        for cluster_name, items in result['clusters'].items():
            print(f"\n[{cluster_name}] -- Contains {len(items)} reviews:")
            for idx, item in enumerate(items[:3]):
                safe_text = item['content'].encode('ascii', errors='replace').decode('ascii')
                print(f"  {idx + 1}. [Score {item['score']}] {safe_text[:130]}...")
                
    except Exception as e:
        print(f"\n[FAILURE] Clustering Test Failed with Error: {e}")
