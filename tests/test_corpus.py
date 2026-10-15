"""Tests for mdrag.corpus.

Contract: docs/specs/phase-1-retrieval.md -> "Corpus contract" and its Exclusions
subsection. Test inventory: same spec -> "Test inventory", Exclusions.
Discovery/frontmatter tests use purpose-built inputs per ADR 0007; the
example-corpus exclusion test is the one case the spec names it for directly.
"""

from pathlib import Path

import pytest

from mdrag.corpus import (
    ExclusionRules,
    discover_notes,
    is_excluded,
    load_corpus,
    load_exclusions,
    load_note,
    parse_mdragignore,
)

EXAMPLES_CORPUS = Path(__file__).parent.parent / "examples" / "corpus"


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_discovers_md_files_relative_to_corpus_root_posix(tmp_path: Path) -> None:
    _write(tmp_path / "a.md", "a")
    _write(tmp_path / "sub" / "b.md", "b")
    exclusions = ExclusionRules(patterns=[], source=str(tmp_path / ".mdragignore"))
    note_paths = discover_notes(tmp_path, exclusions)
    assert note_paths == ["a.md", "sub/b.md"]


def test_frontmatter_parsed_tags_and_area(tmp_path: Path) -> None:
    _write(tmp_path / "note.md", "---\ntags: [a, b]\narea: platform\n---\nBody\n")
    note = load_note(tmp_path, "note.md")
    assert note.tags == ["a", "b"]
    assert note.area == "platform"


def test_missing_frontmatter_yields_empty_tags_and_area_without_raising(tmp_path: Path) -> None:
    _write(tmp_path / "plain.md", "Just a plain markdown note, no frontmatter.\n")
    note = load_note(tmp_path, "plain.md")
    assert note.tags == []
    assert note.area is None


def test_malformed_frontmatter_yields_empty_tags_and_area_without_raising(tmp_path: Path) -> None:
    _write(tmp_path / "broken.md", "---\nnot: [valid: yaml: here\n---\nBody\n")
    note = load_note(tmp_path, "broken.md")
    assert note.tags == []
    assert note.area is None


def test_utf8_decode_failure_names_the_file_and_aborts(tmp_path: Path) -> None:
    bad = tmp_path / "bad.md"
    bad.write_bytes(b"\xff\xfe not valid utf-8")
    with pytest.raises(ValueError, match="bad.md"):
        load_note(tmp_path, "bad.md")


def test_mdragignore_parses_directory_glob_comment_and_blank_lines(tmp_path: Path) -> None:
    ignore = tmp_path / ".mdragignore"
    _write(ignore, "# a comment\n\npeople/\ndrafts/*.md\n")
    patterns = parse_mdragignore(ignore)
    assert patterns == ["people/", "drafts/*.md"]


def test_negation_line_is_rejected(tmp_path: Path) -> None:
    ignore = tmp_path / ".mdragignore"
    _write(ignore, "people/\n!people/jun-okafor.md\n")
    with pytest.raises(ValueError, match="negation"):
        parse_mdragignore(ignore)


def test_missing_mdragignore_loads_with_zero_exclusions(tmp_path: Path) -> None:
    exclusions = load_exclusions(tmp_path)
    assert exclusions.patterns == []


def test_cli_exclude_adds_to_file_patterns_rather_than_replacing(tmp_path: Path) -> None:
    _write(tmp_path / ".mdragignore", "people/\n")
    exclusions = load_exclusions(tmp_path, extra_patterns=["drafts/"])
    assert exclusions.patterns == ["people/", "drafts/"]


def test_directory_form_excludes_everything_under_it() -> None:
    assert is_excluded("people/avery-lin.md", ["people/"])
    assert not is_excluded("reference/glossary.md", ["people/"])


def test_glob_form_star_does_not_cross_slash() -> None:
    assert is_excluded("drafts/one.md", ["drafts/*.md"])
    assert not is_excluded("drafts/sub/two.md", ["drafts/*.md"])


def test_glob_form_double_star_crosses_slash() -> None:
    assert is_excluded("drafts/sub/two.md", ["drafts/**"])


def test_example_corpus_exclusions_remove_people_directory() -> None:
    notes, exclusions = load_corpus(EXAMPLES_CORPUS)
    assert all(not note.note_path.startswith("people/") for note in notes)
    assert "people/" in exclusions.patterns
    assert exclusions.source == str(EXAMPLES_CORPUS / ".mdragignore")


def test_excluded_files_are_never_opened(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write(tmp_path / ".mdragignore", "private/\n")
    _write(tmp_path / "public.md", "---\ntags: [x]\n---\nPublic\n")
    _write(tmp_path / "private" / "secret.md", "---\ntags: [x]\n---\nSecret\n")

    opened: list[Path] = []
    original_read_bytes = Path.read_bytes

    def tracking_read_bytes(self: Path) -> bytes:
        opened.append(self)
        return original_read_bytes(self)

    monkeypatch.setattr(Path, "read_bytes", tracking_read_bytes)

    notes, _ = load_corpus(tmp_path)

    assert [note.note_path for note in notes] == ["public.md"]
    assert (tmp_path / "private" / "secret.md") not in opened


def test_frontmatter_wikilinks_appear_once_per_note(tmp_path: Path) -> None:
    _write(
        tmp_path / "a.md",
        "---\narea: '[[reference/glossary]]'\n---\n"
        "Paragraph one links [[reference/glossary]].\n"
        "Paragraph two links [[reference/glossary]] again.\n",
    )
    _write(tmp_path / "reference" / "glossary.md", "---\ntags: [reference]\n---\nGlossary.\n")
    notes, _ = load_corpus(tmp_path)
    note_a = next(n for n in notes if n.note_path == "a.md")
    assert len(note_a.frontmatter_wikilinks) == 1
    assert note_a.frontmatter_wikilinks[0].resolved == ["reference/glossary.md"]


def test_applied_patterns_and_source_are_exposed(tmp_path: Path) -> None:
    _write(tmp_path / ".mdragignore", "people/\n")
    exclusions = load_exclusions(tmp_path, extra_patterns=["drafts/"])
    assert exclusions.patterns == ["people/", "drafts/"]
    assert exclusions.source == str(tmp_path / ".mdragignore")
