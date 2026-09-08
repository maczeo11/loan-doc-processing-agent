import glob
import logging
import math
import os
import re
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

try:
    import faiss
except ImportError:  # pragma: no cover
    faiss = None

try:
    from rank_bm25 import BM25Okapi
except ImportError:  # pragma: no cover
    BM25Okapi = None

from core.rag.chunking import DocumentChunk, load_and_chunk_policy_file

logger = logging.getLogger("finscan.rag.indexer")


def tokenize_text(text: str) -> List[str]:
    """Lowercase word tokenization for lexical search."""
    return re.findall(r"\w+", text.lower())


class IsolatedIndex:
    """
    Represents an isolated search index for an application or policy corpus.
    Maintains synchronized BM25 lexical and FAISS exact flat dense indices.
    """

    def __init__(self, index_id: str, is_policy: bool = False):
        self.index_id = index_id
        self.is_policy = is_policy
        self.chunks: Dict[str, DocumentChunk] = {}
        self._chunk_ids: List[str] = []
        self._alias_map: Dict[str, str] = {}
        self.faiss_index: Any = None
        self.bm25_index: Any = None
        self._dense_embeddings: Optional[np.ndarray] = None
        self._dimension: Optional[int] = None
        self._corpus_tokens: List[List[str]] = []
        self._tfidf_vectorizer: Any = None

    def add_chunks(
        self,
        chunks: List[DocumentChunk],
        embeddings: Optional[Union[List[List[float]], np.ndarray]] = None,
    ) -> None:
        """
        Add chunks to both lexical BM25 and dense FAISS index.
        Maintains order alignment between chunks, BM25 corpus, and FAISS vectors.
        """
        if not chunks:
            return

        new_chunk_ids: List[str] = []
        new_tokens: List[List[str]] = []

        for chunk in chunks:
            if chunk.chunk_id in self.chunks:
                # Update existing chunk
                self.chunks[chunk.chunk_id] = chunk
            else:
                self.chunks[chunk.chunk_id] = chunk
                self._chunk_ids.append(chunk.chunk_id)
                new_chunk_ids.append(chunk.chunk_id)
                tokens = tokenize_text(chunk.text)
                self._corpus_tokens.append(tokens)
                new_tokens.append(tokens)

            # Map aliases to primary chunk ID
            for alias in chunk.aliases:
                self._alias_map[alias] = chunk.chunk_id

        # 1. Build / Rebuild BM25 lexical index
        if self._corpus_tokens:
            if BM25Okapi is not None:
                self.bm25_index = BM25Okapi(self._corpus_tokens)
                # Standard Lucene / BM25+ smoothing to avoid zero/negative IDF on small dossiers (e.g. N <= 2)
                n_docs = len(self._corpus_tokens)
                for word, idf_val in list(self.bm25_index.idf.items()):
                    if idf_val <= 0.0:
                        df = sum(1 for doc in self._corpus_tokens if word in doc)
                        self.bm25_index.idf[word] = math.log(1.0 + (n_docs - df + 0.5) / (df + 0.5))
            else:  # pragma: no cover
                self.bm25_index = None

        # 2. Build / Update FAISS dense index
        if embeddings is not None:
            emb_array = np.array(embeddings, dtype=np.float32)
            if emb_array.ndim == 1:
                emb_array = emb_array.reshape(1, -1)
            self._add_embeddings_to_faiss(emb_array)
        else:
            # Generate deterministic dense representation using TF-IDF when external embeddings omitted
            self._build_fallback_dense_index()

    def _add_embeddings_to_faiss(self, emb_array: np.ndarray) -> None:
        """Normalizes vectors and updates FAISS exact flat index."""
        if emb_array.shape[0] != len(self._chunk_ids):
            # If batch added, ensure shapes match
            if self._dense_embeddings is not None:
                emb_array = np.vstack([self._dense_embeddings, emb_array])

        dim = emb_array.shape[1]
        self._dimension = dim
        self._dense_embeddings = emb_array.astype(np.float32)

        # L2 normalize for cosine similarity via inner product
        norms = np.linalg.norm(self._dense_embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        normalized_embs = self._dense_embeddings / norms

        if faiss is not None:
            index = faiss.IndexFlatIP(dim)
            index.add(normalized_embs)
            self.faiss_index = index
        else:  # pragma: no cover
            self.faiss_index = None

    def _build_fallback_dense_index(self) -> None:
        """Creates dense TF-IDF vectors as fallback dense representation."""
        if not self._chunk_ids:
            return
        corpus_texts = [self.chunks[cid].text for cid in self._chunk_ids]

        try:
            from sklearn.feature_extraction.text import TfidfVectorizer

            vectorizer = TfidfVectorizer(max_features=256, stop_words="english")
            tfidf_mat = vectorizer.fit_transform(corpus_texts).toarray().astype(np.float32)
            self._tfidf_vectorizer = vectorizer
            self._add_embeddings_to_faiss(tfidf_mat)
        except Exception as e:  # pragma: no cover
            logger.warning(f"Could not build TF-IDF dense fallback: {e}")

    def search_lexical_with_scores(
        self, query: Union[str, List[str]], top_k: int = 10
    ) -> List[Tuple[str, float]]:
        """Search BM25 lexical index returning (chunk_id, bm25_score) pairs."""
        if not self._chunk_ids:
            return []

        if isinstance(query, str):
            query_tokens = tokenize_text(query)
        else:
            query_tokens = [t.lower() for t in query]

        if not query_tokens:
            return [(cid, 0.0) for cid in self._chunk_ids[:top_k]]

        if self.bm25_index is not None:
            scores = self.bm25_index.get_scores(query_tokens)
            ranked_indices = np.argsort(scores)[::-1][:top_k]
            results: List[Tuple[str, float]] = []
            for idx in ranked_indices:
                results.append((self._chunk_ids[idx], float(scores[idx])))
            return results
        else:
            # Pure-python term-frequency fallback if rank_bm25 missing
            scores = []
            for tokens in self._corpus_tokens:
                overlap = sum(1 for t in query_tokens if t in tokens)
                scores.append(overlap)
            ranked_indices = np.argsort(scores)[::-1][:top_k]
            return [(self._chunk_ids[idx], float(scores[idx])) for idx in ranked_indices]

    def search_lexical(
        self, query: Union[str, List[str]], top_k: int = 10
    ) -> List[str]:
        """Search BM25 lexical index returning ranked chunk IDs."""
        ranked = self.search_lexical_with_scores(query, top_k=top_k)
        return [cid for cid, score in ranked]

    def search_dense_with_scores(
        self, query_embedding: Union[List[float], np.ndarray, str], top_k: int = 10
    ) -> List[Tuple[str, float]]:
        """Search dense vector index returning (chunk_id, similarity_score) pairs."""
        if not self._chunk_ids:
            return []

        # If query is string and TF-IDF fallback exists, vectorize it
        if isinstance(query_embedding, str):
            if self._tfidf_vectorizer is not None:
                vec = self._tfidf_vectorizer.transform([query_embedding]).toarray().astype(np.float32)
            else:
                return [(cid, 0.0) for cid in self._chunk_ids[:top_k]]
        else:
            vec = np.array(query_embedding, dtype=np.float32)
            if vec.ndim == 1:
                vec = vec.reshape(1, -1)

        # Normalize query vector
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm

        if self.faiss_index is not None:
            k = min(top_k, len(self._chunk_ids))
            distances, indices = self.faiss_index.search(vec, k)
            results: List[Tuple[str, float]] = []
            for dist, idx in zip(distances[0], indices[0]):
                if idx != -1 and idx < len(self._chunk_ids):
                    results.append((self._chunk_ids[idx], float(dist)))
            return results
        elif self._dense_embeddings is not None:
            # Pure numpy cosine similarity fallback
            norms = np.linalg.norm(self._dense_embeddings, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            normalized = self._dense_embeddings / norms
            sims = np.dot(normalized, vec.T).flatten()
            ranked_indices = np.argsort(sims)[::-1][:top_k]
            return [(self._chunk_ids[i], float(sims[i])) for i in ranked_indices]
        else:
            return [(cid, 0.0) for cid in self._chunk_ids[:top_k]]

    def search_dense(
        self, query_embedding: Union[List[float], np.ndarray, str], top_k: int = 10
    ) -> List[str]:
        """Search dense vector index returning ranked chunk IDs."""
        ranked = self.search_dense_with_scores(query_embedding, top_k=top_k)
        return [cid for cid, score in ranked]

    def get_chunk(self, chunk_id: str) -> Optional[DocumentChunk]:
        """Retrieves chunk by chunk_id or alias."""
        if chunk_id in self.chunks:
            return self.chunks[chunk_id]
        if chunk_id in self._alias_map:
            actual_id = self._alias_map[chunk_id]
            return self.chunks.get(actual_id)
        return None

    def __len__(self) -> int:
        return len(self.chunks)


class IndexManager:
    """
    Manages isolated indices for all applications and the shared policy index.
    Inviolable Rule: Application chunks and policy chunks must never collide.
    """

    def __init__(self):
        self._policy_index: Optional[IsolatedIndex] = None
        self._app_indices: Dict[str, IsolatedIndex] = {}

    def get_or_create_app_index(self, application_id: str) -> IsolatedIndex:
        """Retrieves or creates an isolated index scoped strictly to application_id."""
        if not application_id:
            raise ValueError("application_id must not be empty.")
        if application_id not in self._app_indices:
            self._app_indices[application_id] = IsolatedIndex(index_id=application_id, is_policy=False)
        return self._app_indices[application_id]

    def get_app_index(self, application_id: str) -> Optional[IsolatedIndex]:
        """Retrieves index for application_id if it exists."""
        return self._app_indices.get(application_id)

    def get_policy_index(self) -> IsolatedIndex:
        """Returns the shared policy index."""
        if self._policy_index is None:
            self._policy_index = IsolatedIndex(index_id="policy_corpus", is_policy=True)
        return self._policy_index

    def clear_app_index(self, application_id: str) -> None:
        """Removes the index for an application to free memory."""
        if application_id in self._app_indices:
            del self._app_indices[application_id]

    def clear_all_app_indices(self) -> None:
        """Clears all cached application indices."""
        self._app_indices.clear()

    def load_policy_corpus(self, policy_dir: str = "policies") -> IsolatedIndex:
        """
        Loads all markdown policy files from policy_dir into the shared policy index.
        """
        policy_index = self.get_policy_index()
        if not os.path.exists(policy_dir):
            logger.warning(f"Policy directory {policy_dir} does not exist.")
            return policy_index

        policy_files = glob.glob(os.path.join(policy_dir, "*.md"))
        for p_file in sorted(policy_files):
            try:
                chunks = load_and_chunk_policy_file(p_file)
                policy_index.add_chunks(chunks)
                logger.info(f"Loaded {len(chunks)} chunks from policy file: {p_file}")
            except Exception as e:
                logger.error(f"Failed to load policy file {p_file}: {e}")

        return policy_index

