"""Fixture corpus integrity guard.

Standalone: reads `fixtures/corpus/` directly with `pathlib` and
`python-frontmatter`, independent of `corpus.py`. It tests the fixture, not
the loader - see `fixtures/README.md` and docs/specs/phase-1-retrieval.md,
"Test inventory".
"""

import re
from pathlib import Path

import frontmatter

CORPUS_ROOT = Path(__file__).parent.parent / "fixtures" / "corpus"
EXPECTED_FILE_COUNT = 14

WIKILINK_PATTERN = re.compile(r"\[\[([^\]|#]+)")


def _note_paths() -> list[Path]:
    return sorted(CORPUS_ROOT.rglob("*.md"))


def _stem_index(paths: list[Path]) -> dict[str, Path]:
    return {path.stem: path for path in paths}


def test_expected_file_count_and_every_file_parses() -> None:
    paths = _note_paths()
    assert len(paths) == EXPECTED_FILE_COUNT

    for path in paths:
        text = path.read_text(encoding="utf-8")
        frontmatter.loads(text)


def test_every_note_has_frontmatter_with_tags() -> None:
    for path in _note_paths():
        post = frontmatter.loads(path.read_text(encoding="utf-8"))
        assert "tags" in post.metadata, f"{path} has no 'tags' in frontmatter"
        assert post.metadata["tags"], f"{path} has empty 'tags'"


def test_every_wikilink_resolves_to_an_existing_note() -> None:
    paths = _note_paths()
    stems = _stem_index(paths)

    for path in paths:
        post = frontmatter.loads(path.read_text(encoding="utf-8"))
        for target in WIKILINK_PATTERN.findall(post.content):
            assert target in stems, f"{path}: [[{target}]] does not resolve to any note"


def test_no_self_links() -> None:
    paths = _note_paths()

    for path in paths:
        post = frontmatter.loads(path.read_text(encoding="utf-8"))
        targets = WIKILINK_PATTERN.findall(post.content)
        assert path.stem not in targets, f"{path} links to itself"
