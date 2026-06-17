import logging
from pulse.config import pipeline_config, OPENAI_API_KEY, GEMINI_API_KEY

logger = logging.getLogger("pulse-embeddings")

def get_embeddings(texts: list[str]) -> list[list[float]]:
    """
    Generates embeddings for a list of texts.
    Uses OpenAI or Gemini, falling back to local TF-IDF if API keys are missing.
    """
    if not texts:
        return []

    # Get settings from pipeline_config
    emb_settings = pipeline_config.get("embedding", {})
    provider = emb_settings.get("provider", "openai").lower()
    model = emb_settings.get("model", "text-embedding-3-small")

    # Check key status
    has_openai = provider == "openai" and bool(OPENAI_API_KEY)
    has_gemini = provider == "gemini" and bool(GEMINI_API_KEY)

    if not (has_openai or has_gemini):
        logger.warning("No OpenAI or Gemini API keys found for embeddings. Falling back to local TF-IDF...")
        from sklearn.feature_extraction.text import TfidfVectorizer
        try:
            vectorizer = TfidfVectorizer(stop_words='english', sublinear_tf=True, min_df=1)
            X_tfidf = vectorizer.fit_transform(texts).toarray()
            return X_tfidf.tolist()
        except Exception as e:
            logger.error(f"Local TF-IDF vectorization failed: {e}")
            raise e

    logger.info(f"Generating embeddings for {len(texts)} texts via {provider}...")
    if provider == "openai":
        from openai import OpenAI
        try:
            client = OpenAI(api_key=OPENAI_API_KEY)
            response = client.embeddings.create(model=model, input=texts)
            return [item.embedding for item in response.data]
        except Exception as e:
            logger.error(f"OpenAI embedding call failed: {e}. Falling back to TF-IDF...")
            # Fallback to TF-IDF in case of API failure
            from sklearn.feature_extraction.text import TfidfVectorizer
            vectorizer = TfidfVectorizer(stop_words='english', sublinear_tf=True, min_df=1)
            X_tfidf = vectorizer.fit_transform(texts).toarray()
            return X_tfidf.tolist()
    else: # gemini
        import google.generativeai as genai
        try:
            genai.configure(api_key=GEMINI_API_KEY)
            response = genai.embed_content(
                model="models/text-embedding-004",
                content=texts,
                task_type="clustering"
            )
            return response.get('embedding', [])
        except Exception as e:
            logger.error(f"Gemini embedding call failed: {e}. Falling back to TF-IDF...")
            from sklearn.feature_extraction.text import TfidfVectorizer
            vectorizer = TfidfVectorizer(stop_words='english', sublinear_tf=True, min_df=1)
            X_tfidf = vectorizer.fit_transform(texts).toarray()
            return X_tfidf.tolist()
