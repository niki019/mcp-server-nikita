import re
import json
import time
import logging
from openai import OpenAI
from pulse.config import GROQ_API_KEY, pipeline_config
from pulse.pipeline.quote_validator import validate_quotes

logger = logging.getLogger("pulse-summarizer")

def compute_cluster_score(reviews: list[dict]) -> float:
    """Rank: score = size * (6 - avg_rating)"""
    if not reviews:
        return 0.0
    size = len(reviews)
    ratings = [r.get("score") for r in reviews if r.get("score") is not None]
    avg_rating = sum(ratings) / len(ratings) if ratings else 3.0
    return size * (6.0 - avg_rating)

def select_representative_samples(reviews: list[dict], max_samples: int = 8) -> list[str]:
    """Select representative reviews from the cluster, sorted by thumbsUpCount and length."""
    sorted_reviews = sorted(
        reviews,
        key=lambda r: (r.get("thumbsUpCount") or 0, len(r.get("content") or "")),
        reverse=True
    )
    selected_texts = []
    for r in sorted_reviews[:max_samples]:
        content = r.get("content", "").strip()
        if content:
            selected_texts.append(content)
    return selected_texts

def summarize_cluster(theme_index: int, reviews: list[dict], full_corpus: list[dict]) -> dict:
    """Sends a single cluster to Groq for summarization."""
    # Read parameters from config
    sum_settings = pipeline_config.get("summarization", {})
    model = sum_settings.get("model", "llama-3.3-70b-versatile")
    max_samples = sum_settings.get("max_samples_per_cluster", 8)
    
    samples = select_representative_samples(reviews, max_samples)
    avg_rating = sum([r.get("score", 3) for r in reviews]) / len(reviews) if reviews else 3.0
    
    reviews_xml = "<reviews>\n"
    for i, sample in enumerate(samples):
        reviews_xml += f"  <review id='{i+1}'>{sample}</review>\n"
    reviews_xml += "</reviews>"
    
    system_prompt = (
        "You are an expert product analyst. Analyze the following Play Store reviews for the Groww app. "
        "They belong to a single semantic theme. Your task is to output a structured JSON analysis of this theme.\n\n"
        "Strict JSON Schema:\n"
        "{\n"
        "  \"theme_name\": \"Short, high-level theme title (e.g., App performance & bugs, Payment issues, Login failure)\",\n"
        "  \"summary\": \"1-2 sentences describing the core user issue or feedback detailed in the reviews.\",\n"
        "  \"quotes\": [\"1-2 representative verbatim user quotes extracted from the provided reviews. They must match the review text exactly. Do not hallucinate or rewrite any words.\"],\n"
        "  \"action_ideas\": [\n"
        "    {\n"
        "      \"title\": \"Short action title (e.g. Optimize login latency)\",\n"
        "      \"detail\": \"1 sentence detailing how the engineering/product team can address this issue.\"\n"
        "    }\n"
        "  ]\n"
        "}\n\n"
        "Safety and Accuracy Constraints:\n"
        "1. EVERY string in the 'quotes' array MUST be a verbatim match or exact substring of a sentence/phrase within the provided <reviews> text.\n"
        "2. Do not include markdown formatting, extra keys, or text outside the JSON object.\n"
        "3. Do not include any PII or placeholders in quotes."
    )

    user_content = (
        f"Here is a cluster of reviews representing a common theme.\n"
        f"Total Reviews in Cluster: {len(reviews)}\n"
        f"Average User Rating: {avg_rating:.1f}/5\n\n"
        f"{reviews_xml}\n\n"
        f"Generate the JSON report matching the specified schema."
    )

    # Initialize client
    client = OpenAI(
        base_url="https://api.groq.com/openai/v1",
        api_key=GROQ_API_KEY
    )
    
    retries = 3
    backoff = 2
    
    for attempt in range(retries):
        try:
            logger.info(f"Sending theme request {theme_index} to Groq (attempt {attempt+1})...")
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=800
            )
            
            content = response.choices[0].message.content
            data = json.loads(content)
            
            # Validate quotes
            raw_quotes = data.get("quotes", [])
            valid_quotes = validate_quotes(raw_quotes, reviews, full_corpus)
            data["quotes"] = valid_quotes
            
            return data
            
        except Exception as e:
            logger.error(f"Error calling Groq: {e}")
            if attempt < retries - 1:
                time.sleep(backoff ** (attempt + 1))
            else:
                return {
                    "theme_name": f"Theme {theme_index}",
                    "summary": "Error generating theme summary.",
                    "quotes": [],
                    "action_ideas": []
                }

def generate_pulse_report(clustered_data: dict, full_corpus: list[dict], max_themes: int = 5) -> list[dict]:
    """Sorts and summarizes the top clusters sequentially with pacing."""
    clusters = clustered_data.get("clusters", {})
    if not clusters:
        return []
        
    cluster_scores = []
    for key, reviews in clusters.items():
        score = compute_cluster_score(reviews)
        cluster_scores.append((key, reviews, score))
        
    cluster_scores = sorted(cluster_scores, key=lambda x: x[2], reverse=True)
    
    sum_settings = pipeline_config.get("summarization", {})
    interval = sum_settings.get("request_interval_seconds", 2)
    
    themes = []
    for idx, (key, reviews, score) in enumerate(cluster_scores[:max_themes]):
        if idx > 0:
            logger.info(f"Pacing requests: sleeping for {interval} seconds...")
            time.sleep(interval)
            
        theme_data = summarize_cluster(idx + 1, reviews, full_corpus)
        theme_data["cluster_size"] = len(reviews)
        theme_data["ranking_score"] = round(score, 2)
        themes.append(theme_data)
        
    return themes
