"""Tests for mdrag.embed.

Contract: docs/specs/phase-1-retrieval.md -> "Embedding model", specifically
the `embed.py` contract and Reproducibility subsections. Test inventory:
same spec -> "Test inventory", Retrieval (the embed-level items: unit
length, prefix asymmetry, max_seq_length/dimension read from the model).

These load real, small models from the local sentence-transformers/HF
cache (first run downloads; later runs are offline - see the
Reproducibility subsection). Session-scoped fixtures load each model once.
"""

import numpy as np
import pytest

from mdrag.embed import (
    EmbeddingModel,
    count_over_max_seq_length,
    embed_passages,
    embed_query,
    load_model,
    token_lengths,
)

NO_PREFIX_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
PREFIX_MODEL = "intfloat/e5-small-v2"


@pytest.fixture(scope="session")
def no_prefix_model() -> EmbeddingModel:
    return load_model(NO_PREFIX_MODEL)


@pytest.fixture(scope="session")
def prefix_model() -> EmbeddingModel:
    return load_model(PREFIX_MODEL)


def test_dimensions_and_max_seq_length_come_from_the_loaded_model(
    no_prefix_model: EmbeddingModel,
) -> None:
    # Not hardcoded: both come from the model object itself.
    assert no_prefix_model.dimensions == no_prefix_model._model.get_embedding_dimension()
    assert no_prefix_model.max_seq_length == no_prefix_model._model.max_seq_length
    assert no_prefix_model.dimensions > 0
    assert no_prefix_model.max_seq_length > 0


def test_model_revision_is_a_resolved_commit_sha_not_the_caller_string(
    no_prefix_model: EmbeddingModel,
) -> None:
    # No revision was requested, so the field must still be a concrete,
    # resolved value - never None and never "main".
    assert no_prefix_model.model_revision
    assert no_prefix_model.model_revision != "main"


def test_a_pinned_revision_resolves_to_itself(no_prefix_model: EmbeddingModel) -> None:
    pinned = load_model(NO_PREFIX_MODEL, revision=no_prefix_model.model_revision)
    assert pinned.model_revision == no_prefix_model.model_revision


def test_vectors_are_unit_length_within_tolerance(no_prefix_model: EmbeddingModel) -> None:
    vectors = embed_passages(no_prefix_model, ["one", "two", "three sentences here"])
    norms = np.linalg.norm(vectors, axis=1)
    assert np.allclose(norms, 1.0, atol=1e-3)


def test_embedding_dimension_matches_declared_shape(no_prefix_model: EmbeddingModel) -> None:
    vectors = embed_passages(no_prefix_model, ["a passage"])
    assert vectors.shape == (1, no_prefix_model.dimensions)


def test_empty_input_list_returns_empty_array_of_the_right_shape(
    no_prefix_model: EmbeddingModel,
) -> None:
    vectors = embed_passages(no_prefix_model, [])
    assert vectors.shape == (0, no_prefix_model.dimensions)


def test_model_with_no_declared_prefix_has_empty_prefixes(
    no_prefix_model: EmbeddingModel,
) -> None:
    assert no_prefix_model.query_prefix == ""
    assert no_prefix_model.passage_prefix == ""


def test_model_declaring_prefixes_has_nonempty_prefixes(prefix_model: EmbeddingModel) -> None:
    assert prefix_model.query_prefix != ""
    assert prefix_model.passage_prefix != ""
    assert prefix_model.query_prefix != prefix_model.passage_prefix


def test_query_and_passage_paths_produce_different_vectors_for_a_prefixed_model(
    prefix_model: EmbeddingModel,
) -> None:
    text = "the same identical text"
    query_vec = embed_query(prefix_model, [text])[0]
    passage_vec = embed_passages(prefix_model, [text])[0]
    assert not np.allclose(query_vec, passage_vec)


def test_query_and_passage_paths_produce_identical_vectors_for_an_unprefixed_model(
    no_prefix_model: EmbeddingModel,
) -> None:
    text = "the same identical text"
    query_vec = embed_query(no_prefix_model, [text])[0]
    passage_vec = embed_passages(no_prefix_model, [text])[0]
    assert np.allclose(query_vec, passage_vec)


def test_batch_size_is_a_parameter_and_does_not_change_the_result(
    no_prefix_model: EmbeddingModel,
) -> None:
    texts = ["first", "second", "third", "fourth", "fifth"]
    one_batch = embed_passages(no_prefix_model, texts, batch_size=32)
    small_batches = embed_passages(no_prefix_model, texts, batch_size=2)
    assert np.allclose(one_batch, small_batches, atol=1e-5)


def test_token_lengths_reports_one_count_per_input(no_prefix_model: EmbeddingModel) -> None:
    lengths = token_lengths(no_prefix_model, ["hi", "a slightly longer sentence than that"])
    assert len(lengths) == 2
    assert all(n > 0 for n in lengths)
    assert lengths[1] > lengths[0]


def test_count_over_max_seq_length_counts_inputs_that_would_be_truncated(
    no_prefix_model: EmbeddingModel,
) -> None:
    short_text = "a short sentence"
    long_text = "word " * (no_prefix_model.max_seq_length * 2)
    count = count_over_max_seq_length(no_prefix_model, [short_text, long_text, short_text])
    assert count == 1
