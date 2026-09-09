"""
BGE dense embedding provider (BAAI/bge-small-en-v1.5, 384-dim).

Owned by Member 8 (Sai Mokshith) — RAG pod.

Invariants:
- CI-safe: `sentence-transformers` is optional (see requirements-ci.txt).
  Every public entry point returns None when the model is unavailable,
  and callers MUST fall back to the TF-IDF dense path in indexer.py.
- Core never imports provider SDKs (boto3/redis/celery). sentence-transformers
  is a local ML weight, allowed by the fixed stack (pyproject.toml).
- Set FINSCAN_USE_BGE=0 to force the TF-IDF fallback (deterministic CI / eval).
"""

import logging
import os
from typing import List, Optional

import numpy as np

logger = logging.getLogger("finscan.rag.embeddings")

BGE_MODEL_NAME = "BAAI/bge-small-en-v1.5"
BGE_DIMENSION = 384

_model = None
_model_failed = False


def is_bge_installed() -> bool:
    """True if sentence-transformers is importable (model weights may still need download)."""
    try:
        import sentence_transformers  # noqa: F401

        return True
    except Exception:
        return False


def is_bge_enabled(default: bool = True) -> bool:
    """Kill-switch via FINSCAN_USE_BGE. Accepts 0/false/no/off to disable."""
    raw = os.getenv("FINSCAN_USE_BGE")
    if raw is None:
        return default
    return raw.strip().lower() not in ("0", "false", "no", "off")


def _load_model():
    global _model, _model_failed
    if _model is not None:
        return _model
    if _model_failed:
        return None
    try:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(BGE_MODEL_NAME)
        logger.info(f"Loaded BGE embedding model {BGE_MODEL_NAME}")
        return _model
    except Exception as e:
        _model_failed = True
        logger.warning(f"BGE model {BGE_MODEL_NAME} unavailable, using TF-IDF fallback: {e}")
        return None


def embed_texts(texts: List[str]) -> Optional[np.ndarray]:
    """
    Embeds a batch of chunk texts with BGE. Returns float32 array (n, 384),
    or None when disabled / unavailable (caller falls back to TF-IDF).
    """
    if not texts or not is_bge_enabled() or not is_bge_installed():
        return None
    model = _load_model()
    if model is None:
        return None
    try:
        vecs = model.encode(texts, normalize_embeddings=False, show_progress_bar=False)
        return np.asarray(vecs, dtype=np.float32)
    except Exception as e:
        logger.warning(f"BGE batch embedding failed, using TF-IDF fallback: {e}")
        return None


def embed_query(query: str) -> Optional[np.ndarray]:
    """
    Embeds a single retrieval query with BGE. Returns float32 array (1, 384),
    or None when disabled / unavailable.
    """
    if not query or not query.strip():
        return None
    vecs = embed_texts([query])
    if vecs is None:
        return None
    return vecs.reshape(1, -1)
