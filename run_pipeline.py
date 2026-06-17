import os
import json
import logging
from src.ingest import fetch_play_store_reviews
from src.analyze import ReviewClusterer
from src.summarize import ReviewSummarizer

# Configure logging to console
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("run-pipeline")

def run_pulse_pipeline_for_week(iso_week: str):
    print(f"\n=======================================================")
    print(f"Running Review Pulse Pipeline for ISO Week: {iso_week}")
    print(f"=======================================================\n")
    
    # 1. Fetch normalized reviews from cache
    print("Step 1: Loading reviews from cache...")
    reviews_list = fetch_play_store_reviews(iso_week, use_cache=True)
    print(f"Loaded {len(reviews_list)} normalized reviews.")
    
    if not reviews_list:
        print("Error: No reviews found for the specified week in cache.")
        return
        
    # 2. Run clustering
    print("\nStep 2: Clustering reviews to identify themes...")
    clusterer = ReviewClusterer()
    clustered_data = clusterer.cluster_reviews(reviews_list)
    
    print(f"\n  - Clusters identified: {len(clustered_data['clusters'])}")
    print(f"  - Noise reviews: {len(clustered_data['noise'])}")
    
    # 3. Run Summarization and Quote Validation using Groq LLM
    print("\nStep 3: Generating LLM summaries and validating quotes via Groq...")
    summarizer = ReviewSummarizer()
    themes = summarizer.generate_pulse_report(clustered_data, reviews_list, max_themes=5)
    
    # 4. Display Results
    print("\n=======================================================")
    print(f"PIPELINE REPORT: {iso_week}")
    print(f"=======================================================")
    
    for idx, theme in enumerate(themes):
        # Clean unicode characters for safety in Windows console
        theme_name = theme.get('theme_name', '').encode('ascii', errors='replace').decode('ascii')
        summary = theme.get('summary', '').encode('ascii', errors='replace').decode('ascii')
        
        print(f"\nTheme {idx + 1}: {theme_name}")
        print(f"   Ranking Score: {theme.get('ranking_score')} | Reviews: {theme.get('cluster_size')}")
        print(f"   Summary: {summary}")
        
        print(f"\n   Validated Verbatim Quotes:")
        quotes = theme.get("quotes", [])
        if quotes:
            for q in quotes:
                safe_quote = q.encode('ascii', errors='replace').decode('ascii')
                print(f"     - \"{safe_quote}\"")
        else:
            print("     - (No quotes passed validation)")
            
        print(f"\n   Action Ideas:")
        actions = theme.get("action_ideas", [])
        for a in actions:
            safe_title = a.get('title', '').encode('ascii', errors='replace').decode('ascii')
            safe_detail = a.get('detail', '').encode('ascii', errors='replace').decode('ascii')
            print(f"     - Title: {safe_title}")
            print(f"       Detail: {safe_detail}")
            
    print(f"\n=======================================================")
    print("Pipeline run completed successfully.")
    print(f"=======================================================\n")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run the reviews pulse analysis and summarization pipeline.")
    parser.add_argument("--iso-week", type=str, default="2026-W24", help="ISO week to process (e.g. 2026-W24)")
    args = parser.parse_args()
    
    run_pulse_pipeline_for_week(args.iso_week)
