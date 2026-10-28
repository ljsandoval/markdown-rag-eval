"""Single lexical scan of markdown text: code ranges and ATX headings.

Contract: docs/specs/phase-1-retrieval.md -> "Chunking rules" and "Wikilink
extraction and resolution" -> Extraction.

`wikilinks.extract` needs to know which character ranges are code (so it can
skip links inside them); `chunker.chunk` needs ATX headings that are not
inside a fenced block. Both questions depend on the same fence-tracking pass
over the text, so this module does that pass once and hands back both
derived facts. It imports nothing from this project, so no import cycle can
route through it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_FENCE_RE = re.compile(r"^[ \t]*(`{3,}|~{3,})")
_INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")


@dataclass(frozen=True)
class Heading:
    level: int
    text: str
    line_start: int  # char offset of the heading line's start


@dataclass(frozen=True)
class Scan:
    code_ranges: list[tuple[int, int]]  # fenced blocks and inline code spans
    headings: list[Heading]  # ATX headings outside fences, in order


def scan(text: str) -> Scan:
    """One pass: fence-and-inline-code ranges, plus every ATX heading outside a fence."""
    code_ranges: list[tuple[int, int]] = []
    headings: list[Heading] = []
    pos = 0
    fence_char: str | None = None
    fence_len = 0
    for line in text.splitlines(keepends=True):
        line_start = pos
        pos += len(line)
        stripped = line.rstrip("\n")
        marker_match = _FENCE_RE.match(stripped)
        marker = marker_match.group(1) if marker_match else None
        if fence_char is None:
            if marker is not None:
                fence_char = marker[0]
                fence_len = len(marker)
                code_ranges.append((line_start, pos))
                continue
            heading_match = _HEADING_RE.match(stripped)
            if heading_match:
                headings.append(
                    Heading(
                        level=len(heading_match.group(1)),
                        text=heading_match.group(2).strip(),
                        line_start=line_start,
                    )
                )
            for m in _INLINE_CODE_RE.finditer(stripped):
                code_ranges.append((line_start + m.start(), line_start + m.end()))
        else:
            code_ranges.append((line_start, pos))
            if marker is not None and marker[0] == fence_char and len(marker) >= fence_len:
                fence_char = None
                fence_len = 0
    return Scan(code_ranges=code_ranges, headings=headings)
