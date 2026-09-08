"""
FAISS exact index builder and manager.

Rules from AGENTS.md:
- Hard index isolation: One index per application plus one approved policy index.
- FAISS exact search (IndexFlatIP or IndexFlatL2) - the corpus is small (<50 pages).
- Lexical BM25 index built in parallel for RRF fusion.
- Server code selects the index before retrieval; never selected by user/model input.
"""

from typing import List, Dict, Optional
from core.rag.chunking import DocumentChunk


class IsolatedIndex:
    """Represents an isolated search index for an application or policy corpus."""

    def __init__(self, index_id: str, is_policy: bool = False):
        self.index_id = index_id
        self.is_policy = is_policy
        self.chunks: Dict[str, DocumentChunk] = {}
        self.faiss_index = None
        self.bm25_index = None

    def add_chunks(self, chunks: List[DocumentChunk], embeddings: Optional[List[List[float]]] = None) -> None:
        """Add chunks to lexical and dense index."""
        # Sai Mokshith to implement exact FAISS flat index + BM25
        for chunk in chunks:
            self.chunks[chunk.chunk_id] = chunk

    def search_dense(self, query_embedding: List[float], top_k: int = 10) -> List[str]:
        """Search dense vector index returning chunk IDs."""
        return list(self.chunks.keys())[:top_k]

    def search_lexical(self, query_tokens: List[str], top_k: int = 10) -> List[str]:
        """Search BM25 lexical index returning chunk IDs."""
        return list(self.chunks.keys())[:top_k]


class IndexManager:
    """Manages isolated indices for all applications and the shared policy index."""

    def __init__(self):
        self._policy_index: Optional[IsolatedIndex] = None
        self._app_indices: Dict[str, IsolatedIndex] = {}

    def get_or_create_app_index(self, application_id: str) -> IsolatedIndex:
        if application_id not in self._app_indices:
            self._app_indices[application_id] = IsolatedIndex(index_id=application_id, is_policy=False)
        return self._app_indices[application_id]

    def get_policy_index(self) -> IsolatedIndex:
        if self._policy_index is None:
            self._policy_index = IsolatedIndex(index_id="policy_corpus", is_policy=True)
        return self._policy_index
