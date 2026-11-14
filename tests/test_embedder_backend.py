"""Embedding-backend provenance: which backend ran, strict mode, no hash caching."""

from __future__ import annotations

import sys
import types
from pathlib import Path

import numpy as np
import pytest

from src.module2_rag.embedder import HASH_FALLBACK_BACKEND, ExploitEmbedder

MINILM = "sentence_transformers:all-MiniLM-L6-v2"


def _exploit(idx: int) -> dict:
    return {
        "exploit_id": f"e{idx}",
        "bridge": f"Bridge{idx}",
        "vulnerability_class": "fake_deposit",
        "summary": f"Summary {idx} forged message relay",
    }


@pytest.fixture
def no_sentence_transformers(monkeypatch: pytest.MonkeyPatch) -> None:
    # A None entry in sys.modules makes ``import sentence_transformers`` raise ImportError.
    monkeypatch.setitem(sys.modules, "sentence_transformers", None)


@pytest.fixture
def fake_sentence_transformers(monkeypatch: pytest.MonkeyPatch) -> None:
    mod = types.ModuleType("sentence_transformers")

    class SentenceTransformer:  # minimal stand-in, 384-d like all-MiniLM-L6-v2
        def __init__(self, name: str) -> None:
            self.name = name

        def encode(self, texts, normalize_embeddings=False):
            rows = []
            for t in texts:
                v = np.zeros(384, dtype=np.float32)
                v[len(t) % 384] = 1.0
                v[0] += 0.5
                rows.append(v)
            return np.stack(rows)

    mod.SentenceTransformer = SentenceTransformer
    monkeypatch.setitem(sys.modules, "sentence_transformers", mod)


@pytest.fixture
def cache_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("BRIDGESENTRY_EMBEDDING_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("BRIDGESENTRY_EMBEDDING_CACHE", "1")
    return tmp_path


def test_hash_fallback_is_recorded_and_never_cached(no_sentence_transformers, cache_dir, monkeypatch):
    monkeypatch.setenv("BRIDGESENTRY_REQUIRE_SEMANTIC_EMBEDDING", "0")
    emb = ExploitEmbedder()
    emb.build_index([_exploit(1), _exploit(2)])
    assert emb.backend == HASH_FALLBACK_BACKEND
    assert emb._matrix.shape == (2, 256)
    assert not list(cache_dir.glob("*.npy")), "hash vectors must not be cached under the MiniLM key"


def test_strict_mode_refuses_hash_fallback(no_sentence_transformers, cache_dir, monkeypatch):
    monkeypatch.setenv("BRIDGESENTRY_REQUIRE_SEMANTIC_EMBEDDING", "1")
    emb = ExploitEmbedder()
    with pytest.raises(RuntimeError, match="forbids the hash fallback"):
        emb.build_index([_exploit(1)])


def test_semantic_backend_is_recorded(fake_sentence_transformers, cache_dir, monkeypatch):
    monkeypatch.setenv("BRIDGESENTRY_REQUIRE_SEMANTIC_EMBEDDING", "1")
    emb = ExploitEmbedder()
    emb.build_index([_exploit(1), _exploit(2)])
    assert emb.backend == MINILM
    assert emb._matrix.shape == (2, 384)
    assert emb.search("forged message relay", top_k=1)


def test_cache_hit_reports_semantic_backend(fake_sentence_transformers, cache_dir, monkeypatch):
    monkeypatch.setenv("BRIDGESENTRY_REQUIRE_SEMANTIC_EMBEDDING", "1")
    ExploitEmbedder().build_index([_exploit(1)])
    assert len(list(cache_dir.glob("*.npy"))) == 1
    emb2 = ExploitEmbedder()
    emb2.build_index([_exploit(1)])
    assert emb2.backend == MINILM


def test_index_query_dimension_mismatch_raises(cache_dir, monkeypatch):
    monkeypatch.setenv("BRIDGESENTRY_EMBEDDING_CACHE", "0")
    dims = iter([8, 4])

    def fake_encode(self, texts):
        return np.ones((len(texts), next(dims)), dtype=np.float32)

    monkeypatch.setattr(ExploitEmbedder, "_encode_texts", fake_encode)
    emb = ExploitEmbedder()
    emb.build_index([_exploit(1)])
    with pytest.raises(RuntimeError, match="dimension mismatch"):
        emb.search("q", top_k=1)
