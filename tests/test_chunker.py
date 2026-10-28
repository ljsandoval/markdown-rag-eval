"""Tests for mdrag.chunker.

Contract: docs/specs/phase-1-retrieval.md -> "Chunking rules" and the `Chunk`
model under "Data shapes". Test inventory: same spec -> "Test inventory",
Chunker.

Inputs here are purpose-built string literals, per ADR 0005 and issue #4's
decided reading of the Test Inventory: the module suite never reads
`examples/corpus/` directly, so that corpus can change or disappear without
touching a single test here.
"""

from mdrag.chunker import chunk
from mdrag.corpus import parse_frontmatter


def test_heading_inside_fenced_code_block_does_not_split_a_chunk() -> None:
    body = "# Title\n\n```\n## not a heading\ncode here\n```\n\nMore text.\n"
    chunks = chunk("note.md", body, [], None)
    assert len(chunks) == 1
    assert chunks[0].heading == "Title"
    assert "## not a heading" in chunks[0].text
    assert "More text." in chunks[0].text


def test_markdown_table_emerges_in_exactly_one_chunk() -> None:
    table = "| A | B |\n|---|---|\n| 1 | 2 |\n| 3 | 4 |\n"
    body = f"# Heading\n\n{table}\n## Next\nmore\n"
    chunks = chunk("note.md", body, [], None)
    containing = [c for c in chunks if table.strip() in c.text]
    assert len(containing) == 1


def test_mermaid_fence_emerges_in_exactly_one_chunk() -> None:
    mermaid = "```mermaid\ngraph TD\n## not a heading\nA --> B\n```\n"
    body = f"# Heading\n\n{mermaid}\n## Next\nmore\n"
    chunks = chunk("note.md", body, [], None)
    containing = [c for c in chunks if mermaid.strip() in c.text]
    assert len(containing) == 1


def test_content_before_first_heading_becomes_heading_none_chunk() -> None:
    body = "Some preamble text.\n\n# First Heading\nBody text.\n"
    chunks = chunk("note.md", body, [], None)
    assert chunks[0].heading is None
    assert chunks[0].heading_level is None
    assert "Some preamble text." in chunks[0].text
    assert chunks[1].heading == "First Heading"


def test_breadcrumb_is_correct_for_a_four_level_deep_heading() -> None:
    body = "# A\nintro\n## B\nmid\n### C\ndeep\n#### D\ndeepest\n"
    chunks = chunk("note.md", body, [], None)
    last = chunks[-1]
    assert last.heading == "D"
    assert last.heading_level == 4
    assert last.breadcrumb == ["A", "B", "C"]


def test_char_start_and_char_end_slice_the_body_back_to_chunk_text_exactly() -> None:
    body = "# A\nSome text here.\n## B\nMore text.\n"
    chunks = chunk("note.md", body, [], None)
    for c in chunks:
        assert body[c.char_start : c.char_end] == c.text


def test_frontmatter_keys_never_appear_in_any_chunk_text() -> None:
    raw = "---\ntags: [a, b]\narea: platform\n---\n# Heading\nBody text.\n"
    metadata, body = parse_frontmatter(raw)
    chunks = chunk("note.md", body, ["a", "b"], "platform")
    for c in chunks:
        assert "tags:" not in c.text
        assert "---" not in c.text


def test_wikilinks_in_chunk_text_are_extracted_per_chunk() -> None:
    body = "# A\nSee [[glossary]].\n## B\nSee [[other-note]].\n"
    chunks = chunk("note.md", body, [], None)
    assert [link.target for link in chunks[0].wikilinks] == ["glossary"]
    assert [link.target for link in chunks[1].wikilinks] == ["other-note"]
