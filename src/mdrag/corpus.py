"""Discover a corpus directory, parse frontmatter, and honour its exclusions.

Contract: docs/specs/phase-1-retrieval.md -> "Corpus contract" and its Exclusions
subsection, the `Note` model under "Data shapes". Decisions: ADR 0003 (exclusions
belong to the corpus), ADR 0005 (where links live).
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import frontmatter
import yaml
from pydantic import BaseModel

from mdrag import wikilinks
from mdrag.wikilinks import WikiLink

IGNORE_FILENAME = ".mdragignore"


class Note(BaseModel):
    note_path: str
    tags: list[str]
    area: str | None
    frontmatter_wikilinks: list[WikiLink]  # stored ONCE here, never on chunks


@dataclass(frozen=True)
class ExclusionRules:
    patterns: list[str]
    source: str


def _translate_glob(pattern: str) -> re.Pattern[str]:
    out = []
    i, n = 0, len(pattern)
    while i < n:
        if pattern[i : i + 2] == "**":
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return re.compile("^" + "".join(out) + "$")


def _matches_pattern(note_path: str, pattern: str) -> bool:
    if pattern.endswith("/"):
        pattern = pattern + "**"
    return _translate_glob(pattern).fullmatch(note_path) is not None


def is_excluded(note_path: str, patterns: Sequence[str]) -> bool:
    return any(_matches_pattern(note_path, pattern) for pattern in patterns)


def parse_mdragignore(path: Path) -> list[str]:
    """Parse a `.mdragignore` file. Raises on a line attempting negation."""
    patterns = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("!"):
            raise ValueError(f"{path}:{lineno}: negation is not supported: {line!r}")
        patterns.append(stripped)
    return patterns


def load_exclusions(corpus_root: Path, extra_patterns: Sequence[str] = ()) -> ExclusionRules:
    """Load `.mdragignore` from the corpus root, plus any `--exclude` patterns."""
    ignore_path = corpus_root / IGNORE_FILENAME
    file_patterns = parse_mdragignore(ignore_path) if ignore_path.is_file() else []
    return ExclusionRules(patterns=[*file_patterns, *extra_patterns], source=str(ignore_path))


def discover_notes(corpus_root: Path, exclusions: ExclusionRules) -> list[str]:
    """Discover `**/*.md` under the corpus root. Excluded files are never opened."""
    note_paths = []
    for path in corpus_root.rglob("*.md"):
        rel = path.relative_to(corpus_root).as_posix()
        if not is_excluded(rel, exclusions.patterns):
            note_paths.append(rel)
    return sorted(note_paths)


def _iter_frontmatter_links(value: object) -> list[WikiLink]:
    links: list[WikiLink] = []
    if isinstance(value, str):
        links.extend(wikilinks.extract(value))
    elif isinstance(value, list):
        for item in value:
            links.extend(_iter_frontmatter_links(item))
    elif isinstance(value, dict):
        for item in value.values():
            links.extend(_iter_frontmatter_links(item))
    return links


def load_note(corpus_root: Path, note_path: str) -> Note:
    """Parse one note's frontmatter. Missing/malformed frontmatter is not an error."""
    file_path = corpus_root / note_path
    try:
        text = file_path.read_bytes().decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{note_path}: could not decode as UTF-8") from exc

    try:
        post = frontmatter.loads(text)
    except yaml.YAMLError:
        post = frontmatter.Post(text)
    raw_tags = post.metadata.get("tags")
    tags: list[str]
    if isinstance(raw_tags, str):
        tags = [raw_tags]
    elif isinstance(raw_tags, list):
        tags = [str(item) for item in raw_tags]
    else:
        tags = []
    raw_area = post.metadata.get("area")
    area: str | None = raw_area if isinstance(raw_area, str) else None

    frontmatter_links: list[WikiLink] = []
    for value in post.metadata.values():
        frontmatter_links.extend(_iter_frontmatter_links(value))

    return Note(
        note_path=note_path,
        tags=tags,
        area=area,
        frontmatter_wikilinks=frontmatter_links,
    )


def load_corpus(
    corpus_root: Path, extra_excludes: Sequence[str] = ()
) -> tuple[list[Note], ExclusionRules]:
    """Discover, parse and resolve frontmatter links for every note in a corpus."""
    exclusions = load_exclusions(corpus_root, extra_excludes)
    note_paths = discover_notes(corpus_root, exclusions)
    notes = [load_note(corpus_root, path) for path in note_paths]
    for note in notes:
        note.frontmatter_wikilinks = wikilinks.resolve(note.frontmatter_wikilinks, note_paths)
    return notes, exclusions
