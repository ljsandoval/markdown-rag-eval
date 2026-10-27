"""Extract and resolve `[[wikilinks]]`, for any text.

Contract: docs/specs/phase-1-retrieval.md -> "Wikilink extraction and resolution".
Decisions and measurements behind the rules: ADR 0005.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import PurePosixPath
from typing import Literal

from pydantic import BaseModel

_LINK_RE = re.compile(r"(!?)\[\[([^\]]+)\]\]")
_FENCE_RE = re.compile(r"^[ \t]*(`{3,}|~{3,})")
_INLINE_CODE_RE = re.compile(r"`[^`\n]*`")


class WikiLink(BaseModel):
    link_path: str  # post-split, trimmed, .md stripped; full form, separators kept
    target: str  # link_path's final segment: what a basename match uses
    raw: str  # as written, for failure analysis only
    is_embed: bool  # True for ![[...]]
    resolved: list[str]  # note_paths it resolves to. [] = unresolved, 2+ = ambiguous
    resolved_by: Literal["path", "basename", "unresolved"] = "unresolved"


def _split_before_alias_and_heading(inner: str) -> str:
    idx = len(inner)
    for sep in ("|", "#"):
        pos = inner.find(sep)
        if pos != -1:
            idx = min(idx, pos)
    return inner[:idx]


def _skip_ranges(text: str) -> list[tuple[int, int]]:
    """Char ranges to exclude from matching: fenced code blocks, inline code spans."""
    ranges: list[tuple[int, int]] = []
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
                ranges.append((line_start, pos))
                continue
            for m in _INLINE_CODE_RE.finditer(stripped):
                ranges.append((line_start + m.start(), line_start + m.end()))
        else:
            ranges.append((line_start, pos))
            if marker is not None and marker[0] == fence_char and len(marker) >= fence_len:
                fence_char = None
                fence_len = 0
    return ranges


def _in_ranges(pos: int, ranges: list[tuple[int, int]]) -> bool:
    return any(start <= pos < end for start, end in ranges)


def extract(text: str) -> list[WikiLink]:
    """Extract wikilinks from text. Does not resolve targets; see `resolve`."""
    skip_ranges = _skip_ranges(text)
    links: list[WikiLink] = []
    for m in _LINK_RE.finditer(text):
        if _in_ranges(m.start(), skip_ranges):
            continue
        embed_marker, inner = m.group(1), m.group(2)
        is_embed = embed_marker == "!"
        raw_path = _split_before_alias_and_heading(inner).strip()
        if is_embed:
            suffix = PurePosixPath(raw_path.rsplit("/", 1)[-1]).suffix
            if suffix and suffix != ".md":
                continue  # attachment embed: not an edge, not recorded
        link_path = raw_path[:-3] if raw_path.endswith(".md") else raw_path
        if not link_path:
            continue  # same-note reference, e.g. [[#Some Heading]]: not an edge
        links.append(
            WikiLink(
                link_path=link_path,
                target=link_path.rsplit("/", 1)[-1],
                raw=inner,
                is_embed=is_embed,
                resolved=[],
            )
        )
    return links


def resolve(links: Sequence[WikiLink], note_paths: Sequence[str]) -> list[WikiLink]:
    """Resolve each link's target against a corpus index of note paths."""
    full_index: dict[str, list[str]] = {}
    basename_index: dict[str, list[str]] = {}
    for note_path in note_paths:
        stem = note_path[:-3] if note_path.endswith(".md") else note_path
        full_index.setdefault(stem, []).append(note_path)
        basename = stem.rsplit("/", 1)[-1]
        basename_index.setdefault(basename, []).append(note_path)

    resolved_links: list[WikiLink] = []
    for link in links:
        resolved_by: Literal["path", "basename", "unresolved"]
        if "/" in link.link_path:
            candidates = full_index.get(link.link_path)
            if candidates:
                resolved_by = "path"
            else:
                candidates = basename_index.get(link.target, [])
                resolved_by = "basename" if candidates else "unresolved"
        else:
            candidates = basename_index.get(link.target, [])
            resolved_by = "basename" if candidates else "unresolved"
        resolved_links.append(
            link.model_copy(
                update={"resolved": sorted(candidates or []), "resolved_by": resolved_by}
            )
        )
    return resolved_links
