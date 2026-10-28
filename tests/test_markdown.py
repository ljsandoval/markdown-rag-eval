"""Tests for mdrag.markdown.

Contract: docs/specs/phase-1-retrieval.md -> "Package layout" (the single-scan
rationale) and "Chunking rules" rule 3. `wikilinks.py` and `chunker.py` are
covered separately; these exercise the scan itself.
"""

from mdrag.markdown import scan


def test_fenced_block_contents_are_in_code_ranges() -> None:
    text = "before\n```\ninside\n```\nafter\n"
    result = scan(text)
    inside_start = text.index("inside")
    assert any(start <= inside_start < end for start, end in result.code_ranges)
    after_start = text.index("after")
    assert not any(start <= after_start < end for start, end in result.code_ranges)


def test_inline_code_span_is_in_code_ranges() -> None:
    text = "see `this span` here"
    result = scan(text)
    span_start = text.index("this span")
    assert any(start <= span_start < end for start, end in result.code_ranges)


def test_heading_inside_a_fence_is_excluded_from_headings() -> None:
    text = "# Real\n```\n## Not a heading\n```\n"
    result = scan(text)
    assert [h.text for h in result.headings] == ["Real"]


def test_headings_outside_fences_are_reported_in_order_with_level_and_offset() -> None:
    text = "# A\nbody\n## B\nmore\n"
    result = scan(text)
    assert [(h.level, h.text) for h in result.headings] == [(1, "A"), (2, "B")]
    assert text[result.headings[0].line_start :].startswith("# A")
    assert text[result.headings[1].line_start :].startswith("## B")
