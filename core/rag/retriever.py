"""
Hybrid Retrieval (BM25 Lexical + BAAI/bge-small-en-v1.5 FAISS Exact).
Fused using Reciprocal Rank Fusion (RRF): sum(1 / (60 + rank)).
Owned by Member 8 (Sai Mokshith).
"""

import logging
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

from core.rag.indexer import IndexManager, IsolatedIndex

logger = logging.getLogger("finscan.rag.retriever")


def reciprocal_rank_fusion(
    lexical_ranked: List[str],
    dense_ranked: List[str],
    k: int = 60,
) -> List[Tuple[str, float]]:
    """
    Combines ranked results from BM25 and dense retrieval using Reciprocal Rank Fusion (RRF).
    Formula from AGENTS.md: Score = sum(1 / (60 + rank))
    Where rank is 1-indexed.
    """
    scores: Dict[str, float] = {}

    for rank, chunk_id in enumerate(lexical_ranked, start=1):
        scores[chunk_id] = scores.get(chunk_id, 0.0) + (1.0 / (k + rank))

    for rank, chunk_id in enumerate(dense_ranked, start=1):
        scores[chunk_id] = scores.get(chunk_id, 0.0) + (1.0 / (k + rank))

    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    return ranked


class HybridRetriever:
    """
    Hybrid Retriever executing parallel lexical BM25 and dense FAISS vector search,
    combining candidates via Reciprocal Rank Fusion (RRF).
    Enforces strict index isolation between applications and the global policy corpus.
    """

    def __init__(
        self,
        index_manager: Optional[IndexManager] = None,
        policy_dir: str = "policies",
    ):
        if index_manager is None:
            self.index_manager = IndexManager()
            self.index_manager.load_policy_corpus(policy_dir=policy_dir)
        else:
            self.index_manager = index_manager
            # Ensure policy index is loaded if empty
            if len(self.index_manager.get_policy_index()) == 0:
                self.index_manager.load_policy_corpus(policy_dir=policy_dir)

        self.policy_dir = policy_dir

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        application_id: Optional[str] = None,
        query_embedding: Optional[Union[List[float], np.ndarray]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Executes hybrid retrieval over the specified index.
        If application_id is None or 'POLICY', searches the isolated policy index.
        If application_id is specified (e.g. 'APP-25195'), searches that dossier index.
        """
        if not query or not query.strip():
            return []

        # 1. Select isolated target index
        target_index: IsolatedIndex
        if application_id is None or application_id.upper() == "POLICY":
            target_index = self.index_manager.get_policy_index()
        else:
            app_idx = self.index_manager.get_app_index(application_id)
            if app_idx is None:
                raise ValueError(
                    f"Application index for '{application_id}' does not exist. "
                    "Ensure dossier pages have been ingested and indexed."
                )
            target_index = app_idx

        if len(target_index) == 0:
            return []

        candidate_k = max(top_k * 3, 10)

        # 2. Parallel BM25 lexical search
        lexical_ranked = target_index.search_lexical(query, top_k=candidate_k)

        # 3. Parallel dense FAISS search
        if query_embedding is not None:
            dense_ranked = target_index.search_dense(query_embedding, top_k=candidate_k)
        else:
            dense_ranked = target_index.search_dense(query, top_k=candidate_k)

        # 4. Reciprocal Rank Fusion (RRF)
        fused_candidates = reciprocal_rank_fusion(lexical_ranked, dense_ranked, k=60)
        top_fused = fused_candidates[:top_k]

        # 5. Format and enrich output results with provenance
        results: List[Dict[str, Any]] = []
        for chunk_id, rrf_score in top_fused:
            chunk = target_index.get_chunk(chunk_id)
            if chunk is None:
                continue

            lex_rank = lexical_ranked.index(chunk_id) + 1 if chunk_id in lexical_ranked else None
            dense_rank = dense_ranked.index(chunk_id) + 1 if chunk_id in dense_ranked else None

            result_item: Dict[str, Any] = {
                "chunk_id": chunk.chunk_id,
                "text": chunk.text,
                "score": round(rrf_score, 6),
                "doc_id": chunk.doc_id,
                "page_number": chunk.page_number,
                "is_policy": chunk.is_policy,
                "lexical_rank": lex_rank,
                "dense_rank": dense_rank,
                "aliases": chunk.aliases,
                "token_count": chunk.token_count,
            }

            if chunk.bounding_box is not None:
                result_item["bounding_box"] = chunk.bounding_box.model_dump()

            result_item["evidence_ref"] = chunk.to_evidence_ref().model_dump()
            results.append(result_item)

        return results

    def retrieve_policy(
        self,
        query: str,
        top_k: int = 5,
        query_embedding: Optional[Union[List[float], np.ndarray]] = None,
    ) -> List[Dict[str, Any]]:
        """Convenience method for retrieving underwriting guidelines from policy corpus."""
        return self.retrieve(
            query=query,
            top_k=top_k,
            application_id="POLICY",
            query_embedding=query_embedding,
        )

    def retrieve_dossier(
        self,
        application_id: str,
        query: str,
        top_k: int = 5,
        query_embedding: Optional[Union[List[float], np.ndarray]] = None,
    ) -> List[Dict[str, Any]]:
        """Convenience method for retrieving facts from an applicant's dossier."""
        if not application_id or application_id.upper() == "POLICY":
            raise ValueError("application_id must be a valid applicant ID.")
        return self.retrieve(
            query=query,
            top_k=top_k,
            application_id=application_id,
            query_embedding=query_embedding,
        )

