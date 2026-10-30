"""Tests for mdrag.baseline.

Contract: docs/specs/phase-1-retrieval.md -> "Baseline" and "Retrieval" (for the
shared deterministic tie-break). Test inventory: same spec -> "Test inventory",
Baseline.

Inputs here are purpose-built `Chunk` instances, the same convention test_chunker.py
uses: the module suite never reads `examples/corpus/` directly.
"""

from mdrag.baseline import K1, B, BM25Baseline, tokenize
from mdrag.chunker import Chunk


def _chunk(note_path: str, text: str, char_start: int = 0) -> Chunk:
    return Chunk(
        note_path=note_path,
        heading=None,
        heading_level=None,
        breadcrumb=[],
        text=text,
        char_start=char_start,
        char_end=char_start + len(text),
        tags=[],
        area=None,
        wikilinks=[],
        char_count=len(text),
    )


def test_tokenize_lowercases_and_splits_on_non_alphanumeric() -> None:
    assert tokenize("Hello, World! It's BM25.") == ["hello", "world", "it", "s", "bm25"]


def test_tokenize_drops_empty_tokens() -> None:
    assert tokenize("  ---  ") == []


def test_tokenize_does_not_stem_or_drop_stop_words() -> None:
    # "running" stays "running" (no stemming), "the" and "a" survive (no stop words).
    assert tokenize("the a running") == ["the", "a", "running"]


def test_pinned_parameters() -> None:
    assert K1 == 1.5
    assert B == 0.75


def test_bm25_scores_are_reproducible_across_runs() -> None:
    chunks = [
        _chunk("a.md", "the quick brown fox jumps over the lazy dog"),
        _chunk("b.md", "a completely unrelated sentence about cats"),
    ]
    bm25 = BM25Baseline(chunks)
    first = [(c.note_path, c.char_start) for c in bm25.retrieve("quick fox", 5)]
    second = [(c.note_path, c.char_start) for c in bm25.retrieve("quick fox", 5)]
    assert first == second


def test_relevant_chunk_ranks_above_irrelevant_chunk() -> None:
    chunks = [
        _chunk("irrelevant.md", "a completely unrelated sentence about cats and dogs"),
        _chunk("relevant.md", "collectors restart procedure for the quality flags system"),
    ]
    bm25 = BM25Baseline(chunks)
    results = bm25.retrieve("quality flags", 2)
    assert results[0].note_path == "relevant.md"


def test_deterministic_tie_break_by_note_path_then_char_start() -> None:
    # No query tokens match any chunk, so every score is 0.0 and the tie-break rule
    # alone decides the order: note_path ascending, then char_start ascending.
    chunks = [
        _chunk("b.md", "nothing in common", char_start=5),
        _chunk("a.md", "nothing in common", char_start=10),
        _chunk("a.md", "nothing in common", char_start=0),
    ]
    bm25 = BM25Baseline(chunks)
    results = bm25.retrieve("zzz_no_match", 3)
    assert [(c.note_path, c.char_start) for c in results] == [
        ("a.md", 0),
        ("a.md", 10),
        ("b.md", 5),
    ]


def test_k_larger_than_chunk_count_returns_everything_without_error() -> None:
    chunks = [_chunk("a.md", "one"), _chunk("b.md", "two")]
    bm25 = BM25Baseline(chunks)
    results = bm25.retrieve("one two", 10)
    assert len(results) == 2


def test_empty_chunk_list_does_not_raise() -> None:
    bm25 = BM25Baseline([])
    assert bm25.retrieve("anything", 5) == []
