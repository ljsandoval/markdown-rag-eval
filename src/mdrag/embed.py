"""Load a local sentence-transformers model, apply its prefix convention,
batch-encode text, and L2-normalize the resulting vectors.

Contract: docs/specs/phase-1-retrieval.md -> "Embedding model", specifically
the `embed.py` contract and Reproducibility subsections. Rationale for
local-only embeddings is ADR 0002.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from huggingface_hub import snapshot_download
from numpy.typing import NDArray
from sentence_transformers import SentenceTransformer

# The prefix convention is a property of the model, carried here rather than
# as a string a caller remembers to prepend - see "The prefix trap". Keyed on
# model_id; a model not listed gets no prefix on either side.
MODEL_PREFIXES: dict[str, tuple[str, str]] = {
    "BAAI/bge-small-en-v1.5": (
        "Represent this sentence for searching relevant passages: ",
        "",
    ),
    "intfloat/e5-small-v2": ("query: ", "passage: "),
}


@dataclass(frozen=True)
class EmbeddingModel:
    """A loaded model plus everything the Reproducibility table requires."""

    model_id: str
    model_revision: str
    dimensions: int
    max_seq_length: int
    query_prefix: str
    passage_prefix: str
    normalized: bool
    _model: SentenceTransformer = field(repr=False, compare=False)


def load_model(model_id: str, revision: str | None = None) -> EmbeddingModel:
    """Load `model_id` from the local sentence-transformers/HF cache.

    `revision` is optional. Either way, `model_revision` on the result is
    the commit sha huggingface_hub resolved for this load, read back after
    loading rather than trusting the caller's (possibly unpinned) string -
    see the Reproducibility subsection and issue #3's review comment on
    this field. `sentence-transformers` does not expose the resolved
    commit on the loaded model object, so resolution goes through
    `huggingface_hub.snapshot_download`, which is the same cache
    `SentenceTransformer` itself reads and costs nothing once it is warm.
    """
    model = SentenceTransformer(model_id, revision=revision)
    resolved_path = snapshot_download(model_id, revision=revision)
    model_revision = Path(resolved_path).name

    dimensions = model.get_embedding_dimension()
    if dimensions is None:
        raise ValueError(f"model {model_id!r} does not report an embedding dimension")
    max_seq_length = model.max_seq_length
    if max_seq_length is None:
        raise ValueError(f"model {model_id!r} does not report a max sequence length")

    query_prefix, passage_prefix = MODEL_PREFIXES.get(model_id, ("", ""))

    return EmbeddingModel(
        model_id=model_id,
        model_revision=model_revision,
        dimensions=dimensions,
        max_seq_length=max_seq_length,
        query_prefix=query_prefix,
        passage_prefix=passage_prefix,
        normalized=True,
        _model=model,
    )


def embed_passages(
    em: EmbeddingModel, texts: list[str], batch_size: int = 32
) -> NDArray[np.float32]:
    """Embed passage-side text: `em.passage_prefix` applied, batched, L2-normalized."""
    return _encode(em, texts, em.passage_prefix, batch_size)


def embed_query(em: EmbeddingModel, texts: list[str], batch_size: int = 32) -> NDArray[np.float32]:
    """Embed query-side text: `em.query_prefix` applied, batched, L2-normalized."""
    return _encode(em, texts, em.query_prefix, batch_size)


def token_lengths(em: EmbeddingModel, texts: list[str]) -> list[int]:
    """True per-input token length (special tokens included, no truncation).

    Used to find inputs that exceed `em.max_seq_length`, which
    `sentence-transformers` would otherwise truncate silently.
    """
    tokenizer = em._model.tokenizer
    return [
        len(tokenizer(text, truncation=False, add_special_tokens=True)["input_ids"])
        for text in texts
    ]


def count_over_max_seq_length(em: EmbeddingModel, texts: list[str]) -> int:
    """How many `texts` would be silently truncated by this model."""
    return sum(1 for length in token_lengths(em, texts) if length > em.max_seq_length)


def _encode(
    em: EmbeddingModel, texts: list[str], prefix: str, batch_size: int
) -> NDArray[np.float32]:
    if not texts:
        return np.empty((0, em.dimensions), dtype=np.float32)
    prefixed = [prefix + text for text in texts]
    vectors: NDArray[np.float32] = em._model.encode(
        prefixed,
        batch_size=batch_size,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    ).astype(np.float32)
    _assert_unit_length(vectors)
    return vectors


def _assert_unit_length(
    vectors: NDArray[np.float32], tolerance: float = 1e-3, sample_size: int = 32
) -> None:
    """Sanity-check a sample rather than trusting the library's normalize flag."""
    if vectors.shape[0] == 0:
        return
    rng = np.random.default_rng(0)
    n = min(sample_size, vectors.shape[0])
    sample_idx = rng.choice(vectors.shape[0], size=n, replace=False)
    norms = np.linalg.norm(vectors[sample_idx], axis=1)
    if not np.allclose(norms, 1.0, atol=tolerance):
        raise AssertionError(f"embeddings are not unit length within {tolerance}: {norms}")
