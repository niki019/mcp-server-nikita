import logging
import numpy as np
from sklearn.cluster import DBSCAN, KMeans
from pulse.pipeline.embeddings import get_embeddings
from pulse.config import pipeline_config

logger = logging.getLogger("pulse-clustering")

def cluster_reviews(reviews_list: list[dict]) -> dict:
    """
    Groups reviews into semantic clusters. Uses DBSCAN with K-Means fallback.
    """
    if not reviews_list:
        return {"clusters": {}, "noise": []}

    texts = [r["content"] for r in reviews_list]
    
    # 1. Fetch Embeddings
    embeddings = get_embeddings(texts)
    if not embeddings:
        return {"clusters": {}, "noise": reviews_list}

    X = np.array(embeddings)
    
    # 2. Normalize embeddings for stable cosine distance
    norms = np.linalg.norm(X, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    X_normalized = X / norms

    # 3. Read clustering parameters from config
    cluster_settings = pipeline_config.get("clustering", {})
    umap_settings = cluster_settings.get("umap", {})
    hdb_settings = cluster_settings.get("hdbscan", {})

    # DBSCAN parameters (equivalent to cosine similarity >= 0.65)
    eps = 0.35
    min_samples = hdb_settings.get("min_samples", 3)
    
    if len(reviews_list) < 15:
        min_samples = 2

    logger.info(f"Running DBSCAN (eps={eps}, min_samples={min_samples})...")
    db = DBSCAN(eps=eps, min_samples=min_samples, metric='cosine')
    labels = db.fit_predict(X_normalized)

    unique_labels = set(labels)
    noise_count = np.sum(labels == -1)

    # 4. Fallback: If DBSCAN labels > 85% as noise, run K-Means
    if (noise_count / len(reviews_list) > 0.85 or len(unique_labels - {-1}) == 0) and len(reviews_list) >= 5:
        num_clusters = max(2, min(5, len(reviews_list) // 10))
        logger.info(f"DBSCAN generated too much noise ({noise_count}/{len(reviews_list)}). Falling back to K-Means (K={num_clusters})...")
        kmeans = KMeans(n_clusters=num_clusters, random_state=42, n_init='auto')
        labels = kmeans.fit_predict(X_normalized)

    # 5. Group reviews by label
    clusters = {}
    noise = []

    for i, label in enumerate(labels):
        review = reviews_list[i]
        if label == -1:
            noise.append(review)
        else:
            cluster_key = f"cluster_{label}"
            if cluster_key not in clusters:
                clusters[cluster_key] = []
            clusters[cluster_key].append(review)

    # Log results
    logger.info(f"Identified {len(clusters)} clusters and {len(noise)} noise reviews.")
    return {
        "clusters": clusters,
        "noise": noise
    }
