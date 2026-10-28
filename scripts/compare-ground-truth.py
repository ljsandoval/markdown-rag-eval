"""Compare this project's wikilink resolution against Obsidian's own.

Obsidian's `app.metadataCache.resolvedLinks` is the authoritative resolver for a
vault. `scripts/obsidian-export-resolved-links.js` exports it; this compares the
export against what `mdrag` produces over the same corpus, and classifies every
disagreement so none of them has to be explained twice.

    uv run python scripts/compare-ground-truth.py \
        --corpus /path/to/corpus --ground-truth /path/to/export.json

Corpus-agnostic: it takes paths and knows nothing about Obsidian beyond the
export's shape. The export belongs wherever the corpus's private measurement
artifacts live, never in this repository (ADR 0003, ADR 0008).

Two things the comparison must do, both learned the hard way:

* **Compare counts, not just pairs.** The maps are keyed by (source, target)
  with a count. A rule that double-counts one link leaves every pair intact and
  changes only its multiplicity, so a set comparison is blind to it. The first
  run found 25 disagreeing pairs plus 14 that agreed on existence and differed
  by one on count.
* **Account for cross-boundary links.** A link from a kept note to an excluded
  note is resolved by Obsidian and then dropped by the export's target filter,
  so it is in neither map. Counted separately here rather than silently lost.

Three disagreement classes are known and intentional (spec's Validation
section, ADR 0005) and are excluded from the exit status; anything else is
**unexplained** and is the only thing that makes it nonzero.

Body links come from `chunker.chunk()`'s output, same as the real pipeline -
not from a local `wikilinks.extract(body)` call - so this validates what
actually gets indexed rather than a parallel reimplementation of it (#4).
"""

from __future__ import annotations

import argparse
import collections
import json
import pathlib
import re
import sys

from mdrag import chunker, wikilinks
from mdrag.corpus import discover_notes, frontmatter_value_links, load_exclusions, parse_frontmatter

Graph = dict[str, dict[str, list[wikilinks.WikiLink]]]

_SELF_HEADING_RE = re.compile(r"\[\[#[^\]]*\]\]")

BASENAME_FALLBACK = "basename fallback"
SAME_NOTE_HEADING = "same-note heading reference"
AMBIGUITY = "ambiguity"


def _note_links(note_path: str, text: str) -> list[wikilinks.WikiLink]:
    metadata, body = parse_frontmatter(text)
    links: list[wikilinks.WikiLink] = []
    for note_chunk in chunker.chunk(note_path, body, tags=[], area=None):
        links.extend(note_chunk.wikilinks)
    for value in metadata.values():
        links.extend(frontmatter_value_links(value))
    return links


def build(corpus: pathlib.Path) -> tuple[Graph, int, dict[str, str]]:
    """Resolve every link in the corpus, keeping the contributing `WikiLink`
    per (source, target) pair so disagreements can be classified, not just
    tallied."""
    exclusions = load_exclusions(corpus)
    kept = discover_notes(corpus, exclusions)
    kept_set = set(kept)
    every_note = [
        path.relative_to(corpus).as_posix()
        for path in sorted(corpus.rglob("*.md"))
        if not path.relative_to(corpus).as_posix().startswith(".obsidian/")
    ]

    graph: Graph = {}
    texts: dict[str, str] = {}
    crossing = 0
    for note_path in kept:
        text = (corpus / note_path).read_text(encoding="utf-8")
        texts[note_path] = text
        contributions: dict[str, list[wikilinks.WikiLink]] = collections.defaultdict(list)
        for link in wikilinks.resolve(_note_links(note_path, text), every_note):
            for target in link.resolved:
                if target in kept_set:
                    contributions[target].append(link)
                else:
                    crossing += 1
        if contributions:
            graph[note_path] = dict(contributions)
    return graph, crossing, texts


def classify_mine_only(links: list[wikilinks.WikiLink]) -> str | None:
    """A pair mdrag has that Obsidian doesn't: basename fallback, or every
    candidate of an ambiguous target. `None` means unexplained."""
    if any(link.resolved_by == "basename" for link in links):
        return BASENAME_FALLBACK
    if any(len(link.resolved) > 1 for link in links):
        return AMBIGUITY
    return None


def classify_count_differs(links: list[wikilinks.WikiLink]) -> str | None:
    """A pair both sides have but disagree on count: only the basename
    fallback is known to rescue an extra link to an already-reached target."""
    if any(link.resolved_by == "basename" for link in links):
        return BASENAME_FALLBACK
    return None


def classify_obsidian_only(source: str, target: str, source_text: str | None) -> str | None:
    """A pair Obsidian has that mdrag doesn't: a same-note `[[#Heading]]`
    reference, which Obsidian resolves to a self-edge and this drops at
    extraction. Confirmed against the source text, never inferred from
    `source == target` alone - a genuine self-link would match that pattern
    too."""
    if source == target and source_text is not None and _SELF_HEADING_RE.search(source_text):
        return SAME_NOTE_HEADING
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--corpus", type=pathlib.Path, required=True)
    ap.add_argument("--ground-truth", type=pathlib.Path, required=True)
    ap.add_argument("--show", type=int, default=10, help="disagreements to list per class")
    args = ap.parse_args()

    truth = json.loads(args.ground_truth.read_text())["resolved"]
    mine, crossing, texts = build(args.corpus)

    mine_pairs = {(s, t) for s, d in mine.items() for t in d}
    truth_pairs = {(s, t) for s, d in truth.items() for t in d}
    agreed = mine_pairs & truth_pairs

    miscounted = [
        (s, t, len(d[t]), truth[s][t])
        for s, d in mine.items()
        for t in d
        if t in truth.get(s, {}) and truth[s][t] != len(d[t])
    ]

    print(f"sources          mine {len(mine):>5}   obsidian {len(truth):>5}")
    print(f"distinct pairs   mine {len(mine_pairs):>5}   obsidian {len(truth_pairs):>5}")
    pct = len(agreed) / len(truth_pairs) if truth_pairs else 0.0
    print(f"  agreeing            {len(agreed):>5}   ({pct:.1%} of obsidian)")
    print(f"  mine only           {len(mine_pairs - truth_pairs):>5}")
    print(f"  obsidian only       {len(truth_pairs - mine_pairs):>5}")
    print(f"  same pair, count differs  {len(miscounted):>5}")
    print(f"cross-boundary links dropped by both      {crossing:>5}")

    classified: dict[str, list[tuple[str, str]]] = collections.defaultdict(list)
    unexplained: list[tuple[str, str, str]] = []

    for source, target in sorted(mine_pairs - truth_pairs):
        label = classify_mine_only(mine[source][target])
        if label is None:
            unexplained.append((source, target, "mine only"))
        else:
            classified[label].append((source, target))

    for source, target in sorted(truth_pairs - mine_pairs):
        label = classify_obsidian_only(source, target, texts.get(source))
        if label is None:
            unexplained.append((source, target, "obsidian only"))
        else:
            classified[label].append((source, target))

    for source, target, mine_n, truth_n in sorted(miscounted):
        label = classify_count_differs(mine[source][target])
        if label is None:
            unexplained.append(
                (source, target, f"count differs (mine {mine_n} / obsidian {truth_n})")
            )
        else:
            classified[label].append((source, target))

    intentional = sum(len(pairs) for pairs in classified.values())
    for label in (BASENAME_FALLBACK, SAME_NOTE_HEADING, AMBIGUITY):
        pairs = classified.get(label, [])
        print(f"\n{label}, {len(pairs)}:")
        for source, target in pairs[: args.show]:
            print(f"  {source}  ->  {target}")

    print(f"\n{len(unexplained)} unexplained:")
    for source, target, why in unexplained[: args.show]:
        print(f"  {source}  ->  {target}   ({why})")

    print(f"\n{intentional} intentional, {len(unexplained)} unexplained.")
    if unexplained:
        print("Every unexplained disagreement needs a named cause before this is trusted.")
    return 1 if unexplained else 0


if __name__ == "__main__":
    sys.exit(main())
