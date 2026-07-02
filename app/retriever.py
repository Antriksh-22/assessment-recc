from dataclasses import dataclass
from typing import List

import numpy as np
from rapidfuzz import fuzz
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

try:
    from rank_bm25 import BM25Okapi
except Exception:
    BM25Okapi = None

try:
    from sentence_transformers import SentenceTransformer
except Exception:
    SentenceTransformer = None

from .catalog import Catalog, CatalogItem


@dataclass
class RetrievedItem:
    item: CatalogItem
    semantic_score: float
    keyword_score: float
    fuzzy_score: float


class HybridRetriever:
    def __init__(self, catalog: Catalog):
        self.catalog = catalog
        self.texts = [item.searchable_text for item in catalog.items]
        self.tokens = [text.split() for text in self.texts]
        self.vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        self.tfidf = self.vectorizer.fit_transform(self.texts)
        self.bm25 = BM25Okapi(self.tokens) if BM25Okapi else None
        self.semantic_model = None
        self.semantic_embeddings = None
        if SentenceTransformer:
            try:
                self.semantic_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2", local_files_only=True)
                self.semantic_embeddings = self.semantic_model.encode(self.texts, normalize_embeddings=True)
            except Exception:
                self.semantic_model = None
                self.semantic_embeddings = None

    def search(self, query: str, top_k: int = 30) -> List[RetrievedItem]:
        query = query.lower().strip()
        if not query:
            return []

        if self.bm25:
            keyword = np.array(self.bm25.get_scores(query.split()), dtype=float)
        else:
            keyword = cosine_similarity(self.vectorizer.transform([query]), self.tfidf).ravel()
        keyword = _normalize(keyword)

        tfidf_semantic = cosine_similarity(self.vectorizer.transform([query]), self.tfidf).ravel()
        if self.semantic_model is not None and self.semantic_embeddings is not None:
            try:
                q = self.semantic_model.encode([query], normalize_embeddings=True)
                semantic = np.dot(self.semantic_embeddings, q[0])
            except Exception:
                semantic = tfidf_semantic
        else:
            semantic = tfidf_semantic
        semantic = _normalize(np.array(semantic, dtype=float))

        fuzzy = np.array([fuzz.partial_ratio(query, item.searchable_text) / 100 for item in self.catalog.items])
        exact_skill = np.array([_exact_skill_boost(query, item) for item in self.catalog.items])
        combined = 0.40 * semantic + 0.30 * keyword + 0.15 * fuzzy + 0.15 * exact_skill
        indices = np.argsort(combined)[::-1][:top_k]
        return [
            RetrievedItem(
                item=self.catalog.items[i],
                semantic_score=float(semantic[i]),
                keyword_score=float(keyword[i]),
                fuzzy_score=float(fuzzy[i]),
            )
            for i in indices
        ]


def _normalize(values: np.ndarray) -> np.ndarray:
    if values.size == 0:
        return values
    low = float(values.min())
    high = float(values.max())
    if high - low < 1e-9:
        return np.zeros_like(values, dtype=float)
    return (values - low) / (high - low)


def _exact_skill_boost(query: str, item: CatalogItem) -> float:
    name = item.name.lower()
    boosts = {
        "aws": ["amazon web services", "aws"],
        "amazon web services": ["amazon web services", "aws"],
        "cloud": ["amazon web services", "aws"],
        "docker": ["docker"],
        "container": ["docker"],
        "core java": ["core java"],
        "java": ["core java"],
        "spring": ["spring"],
        "sql": ["sql (new)"],
    }
    score = 0.0
    for query_term, name_terms in boosts.items():
        if query_term in query and any(name_term in name for name_term in name_terms):
            score = max(score, 1.0)
    return score
