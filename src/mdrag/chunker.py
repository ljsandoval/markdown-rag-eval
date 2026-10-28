"""Split a note's body into heading-aware chunks.

Contract: docs/specs/phase-1-retrieval.md -> "Chunking rules" and the `Chunk`
model under "Data shapes". Wikilink rules: "Wikilink extraction and
resolution", ADR 0005.
"""

from __future__ import annotations

from pydantic import BaseModel

from mdrag import markdown, wikilinks
from mdrag.wikilinks import WikiLink


class Chunk(BaseModel):
    note_path: str
    heading: str | None
    heading_level: int | None
    breadcrumb: list[str]
    text: str
    char_start: int
    char_end: int
    tags: list[str]
    area: str | None
    wikilinks: list[WikiLink]
    char_count: int


def chunk(note_path: str, body: str, tags: list[str], area: str | None) -> list[Chunk]:
    """Split already-stripped body text at ATX headings. Links are extracted,
    not resolved - resolution needs a corpus-wide note index the caller holds."""
    headings = markdown.scan(body).headings

    spans: list[tuple[int, int, markdown.Heading | None]] = []
    if not headings:
        spans.append((0, len(body), None))
    else:
        if headings[0].line_start > 0:
            spans.append((0, headings[0].line_start, None))
        for i, h in enumerate(headings):
            end = headings[i + 1].line_start if i + 1 < len(headings) else len(body)
            spans.append((h.line_start, end, h))

    chunks: list[Chunk] = []
    stack: list[tuple[int, str]] = []
    for start, end, heading in spans:
        text = body[start:end]
        if not text:
            continue
        if heading is None:
            breadcrumb: list[str] = []
        else:
            while stack and stack[-1][0] >= heading.level:
                stack.pop()
            breadcrumb = [entry_text for _, entry_text in stack]
            stack.append((heading.level, heading.text))
        chunks.append(
            Chunk(
                note_path=note_path,
                heading=heading.text if heading else None,
                heading_level=heading.level if heading else None,
                breadcrumb=breadcrumb,
                text=text,
                char_start=start,
                char_end=end,
                tags=tags,
                area=area,
                wikilinks=wikilinks.extract(text),
                char_count=len(text),
            )
        )
    return chunks
