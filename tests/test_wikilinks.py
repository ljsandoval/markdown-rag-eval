"""Tests for mdrag.wikilinks.

Contract: docs/specs/phase-1-retrieval.md -> "Wikilink extraction and resolution".
Test inventory: same spec -> "Test inventory", Wikilinks. Inputs here are
purpose-built per ADR 0007; the example corpus exercises almost none of these
cases and is not used for them.
"""

from mdrag.wikilinks import extract, resolve


def test_wikilink_inside_fenced_code_block_is_not_extracted() -> None:
    text = "intro\n```\n[[not-a-link]]\n```\nafter [[a-link]]\n"
    links = extract(text)
    assert [link.target for link in links] == ["a-link"]


def test_wikilink_inside_inline_code_span_is_not_extracted() -> None:
    text = "See `[[not-a-link]]` but also [[a-link]]."
    links = extract(text)
    assert [link.target for link in links] == ["a-link"]


def test_alias_and_heading_fragment_both_yield_bare_target() -> None:
    links = extract("[[note|alias]] and [[note#heading]]")
    assert [link.target for link in links] == ["note", "note"]


def test_trailing_md_and_padding_whitespace_are_stripped() -> None:
    links = extract("[[ note.md ]]")
    assert len(links) == 1
    assert links[0].target == "note"


def test_path_form_target_resolves_by_full_path_when_it_exists() -> None:
    links = extract("[[people/jun-okafor]]")
    resolved = resolve(links, ["people/jun-okafor.md", "other/jun-okafor.md"])
    assert resolved[0].resolved == ["people/jun-okafor.md"]


def test_path_form_target_falls_back_to_basename_when_full_path_absent() -> None:
    links = extract("[[wrong-folder/glossary]]")
    resolved = resolve(links, ["reference/glossary.md"])
    assert resolved[0].resolved == ["reference/glossary.md"]


def test_resolution_is_case_sensitive() -> None:
    links = extract("[[glossary]]")
    resolved = resolve(links, ["reference/Glossary.md"])
    assert resolved[0].resolved == []


def test_ambiguous_target_resolves_to_every_candidate() -> None:
    links = extract("[[station]]")
    resolved = resolve(links, ["reference/station.md", "archive/station.md"])
    assert resolved[0].resolved == ["archive/station.md", "reference/station.md"]


def test_unresolved_target_is_recorded_and_does_not_raise() -> None:
    links = extract("[[nowhere]]")
    resolved = resolve(links, ["reference/glossary.md"])
    assert resolved[0].resolved == []


def test_embed_of_a_note_is_an_edge_flagged_as_embed() -> None:
    links = extract("![[glossary]]")
    assert len(links) == 1
    assert links[0].is_embed is True
    assert links[0].target == "glossary"


def test_embed_of_an_attachment_is_not_an_edge() -> None:
    links = extract("![[image.png]]")
    assert links == []


def test_plain_link_is_not_flagged_as_embed() -> None:
    links = extract("[[glossary]]")
    assert links[0].is_embed is False
