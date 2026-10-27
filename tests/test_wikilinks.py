"""Tests for mdrag.wikilinks.

Contract: docs/specs/phase-1-retrieval.md -> "Wikilink extraction and resolution".
Test inventory: same spec -> "Test inventory", Wikilinks. Inputs here are
purpose-built per ADR 0007; the example corpus exercises almost none of these
cases and is not used for them.
"""

from mdrag.wikilinks import WikiLink, extract, resolve


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


def test_link_path_keeps_the_path_form_that_target_reduces_away() -> None:
    links = extract("[[people/jun-okafor.md]]")
    assert links[0].link_path == "people/jun-okafor"
    assert links[0].target == "jun-okafor"


def test_resolve_reads_the_model_rather_than_reparsing_raw() -> None:
    """A link built directly must resolve: resolution consumes fields, not `raw`."""
    link = WikiLink(
        link_path="people/jun-okafor", target="jun-okafor", raw="", is_embed=False, resolved=[]
    )
    resolved = resolve([link], ["people/jun-okafor.md", "other/jun-okafor.md"])
    assert resolved[0].resolved == ["people/jun-okafor.md"]


def test_same_note_heading_reference_is_not_recorded_as_a_link() -> None:
    links = extract("See [[#Some Heading]] and also [[#Another Heading]] below.")
    assert links == []


def test_resolved_by_is_path_basename_or_unresolved_matching_empty_resolved() -> None:
    links = extract("[[people/jun-okafor]] [[glossary]] [[nowhere]]")
    resolved = resolve(links, ["people/jun-okafor.md", "reference/glossary.md"])
    by_target = {link.target: link for link in resolved}
    assert by_target["jun-okafor"].resolved_by == "path"
    assert by_target["glossary"].resolved_by == "basename"
    assert by_target["nowhere"].resolved_by == "unresolved"
    for link in resolved:
        assert (link.resolved_by == "unresolved") == (link.resolved == [])


def test_path_form_target_resolving_only_by_basename_fallback_is_recorded_as_such() -> None:
    links = extract("[[wrong-folder/glossary]]")
    resolved = resolve(links, ["reference/glossary.md"])
    assert resolved[0].resolved_by == "basename"
