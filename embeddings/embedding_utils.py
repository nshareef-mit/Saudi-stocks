from typing import List

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


def load_embedding_model(model_name: str = "BAAI/bge-m3") -> SentenceTransformer:
    """Load a SentenceTransformer embedding model."""
    return SentenceTransformer(model_name)


def embed_texts(model: SentenceTransformer, texts: List[str], normalize_embeddings: bool = True) -> np.ndarray:
    """Generate embeddings for a list of texts."""
    return model.encode(texts, normalize_embeddings=normalize_embeddings)


def compute_cosine_similarity(embeddings: np.ndarray) -> np.ndarray:
    """Compute cosine similarity between a set of embeddings."""
    return cosine_similarity(embeddings)
