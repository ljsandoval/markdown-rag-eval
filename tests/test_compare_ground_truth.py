"""Tests for scripts/compare-ground-truth.py's divergence classifier.

Contract: docs/specs/phase-1-retrieval.md -> "Wikilink extraction and
resolution" -> Validation, which enumerates the three known divergence
classes. Decisions behind them are ADR 0005.

Synthetic inputs only, per issue #18 - the classifier must not need the
private corpus to be tested.
"""

import importlib.util
import pathlib
import types

from mdrag.wikilinks import WikiLink


def _load_module() -> types.ModuleType:
    path = pathlib.Path(__file__).parent.parent / "scripts" / "compare-ground-truth.py"
    spec = importlib.util.spec_from_file_location("compare_ground_truth", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cgt = _load_module()


def _link(resolved: list[str], resolved_by: str) -> WikiLink:
    return WikiLink(
        link_path="x",
        target="x",
        raw="x",
        is_embed=False,
        resolved=resolved,
        resolved_by=resolved_by,  # type: ignore[arg-type]
    )


def test_mine_only_pair_with_basename_link_is_basename_fallback() -> None:
    links = [_link(["a.md"], "basename")]
    assert cgt.classify_mine_only(links) == cgt.BASENAME_FALLBACK


def test_mine_only_pair_with_ambiguous_link_is_ambiguity() -> None:
    links = [_link(["a.md", "b.md"], "path")]
    assert cgt.classify_mine_only(links) == cgt.AMBIGUITY


def test_mine_only_pair_matching_no_class_is_unexplained() -> None:
    links = [_link(["a.md"], "path")]
    assert cgt.classify_mine_only(links) is None


def test_count_differs_with_basename_contribution_is_basename_fallback() -> None:
    links = [_link(["a.md"], "path"), _link(["a.md"], "basename")]
    assert cgt.classify_count_differs(links) == cgt.BASENAME_FALLBACK


def test_count_differs_with_no_basename_contribution_is_unexplained() -> None:
    links = [_link(["a.md"], "path"), _link(["a.md"], "path")]
    assert cgt.classify_count_differs(links) is None


def test_obsidian_only_self_pair_confirmed_by_source_text_is_same_note() -> None:
    label = cgt.classify_obsidian_only("note.md", "note.md", "See [[#Some Heading]] above.")
    assert label == cgt.SAME_NOTE_HEADING


def test_obsidian_only_self_pair_unconfirmed_by_source_text_is_unexplained() -> None:
    label = cgt.classify_obsidian_only("note.md", "note.md", "No heading reference here.")
    assert label is None


def test_obsidian_only_self_pair_with_no_source_text_available_is_unexplained() -> None:
    assert cgt.classify_obsidian_only("note.md", "note.md", None) is None


def test_obsidian_only_non_self_pair_is_never_same_note() -> None:
    label = cgt.classify_obsidian_only("a.md", "b.md", "See [[#Some Heading]] above.")
    assert label is None
