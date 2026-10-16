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

TODO, in two steps, in this order. **#17** gives frontmatter stripping the one
home the Corpus contract specifies, and `_parse` below is replaced by that
function. **#4** then makes body links come from the chunker's output rather
than from a local `extract` call. Both are specified but unbuilt, so this
follows the spec as closely as currently possible and flags the unification
forward.
"""

from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys

import frontmatter
import yaml

from mdrag import wikilinks
from mdrag.corpus import discover_notes, load_exclusions


def _parse(text: str) -> tuple[dict[str, object], str]:
    """Split frontmatter from body, treating unparseable YAML as absent metadata.

    Mirrors `corpus.load_note`'s tolerance. See the module TODO: the stripping
    rule is specified to have exactly one home, and this is not it.
    """
    try:
        post = frontmatter.loads(text)
    except yaml.YAMLError:
        return {}, text
    return post.metadata, post.content


def _note_links(text: str) -> list[wikilinks.WikiLink]:
    metadata, body = _parse(text)
    links = list(wikilinks.extract(body))
    for value in metadata.values():
        items = [value] if isinstance(value, str) else value if isinstance(value, list) else []
        for item in items:
            if isinstance(item, str):
                links.extend(wikilinks.extract(item))
    return links


def build(corpus: pathlib.Path) -> tuple[dict[str, dict[str, int]], int]:
    """Resolve every link in the corpus, and count links leaving it."""
    exclusions = load_exclusions(corpus)
    kept = discover_notes(corpus, exclusions)
    kept_set = set(kept)
    every_note = [
        path.relative_to(corpus).as_posix()
        for path in sorted(corpus.rglob("*.md"))
        if not path.relative_to(corpus).as_posix().startswith(".obsidian/")
    ]

    graph: dict[str, dict[str, int]] = {}
    crossing = 0
    for note_path in kept:
        text = (corpus / note_path).read_text(encoding="utf-8")
        counts: collections.Counter[str] = collections.Counter()
        for link in wikilinks.resolve(_note_links(text), every_note):
            for target in link.resolved:
                if target in kept_set:
                    counts[target] += 1
                else:
                    crossing += 1
        if counts:
            graph[note_path] = dict(counts)
    return graph, crossing


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--corpus", type=pathlib.Path, required=True)
    ap.add_argument("--ground-truth", type=pathlib.Path, required=True)
    ap.add_argument("--show", type=int, default=10, help="disagreements to list per class")
    args = ap.parse_args()

    truth = json.loads(args.ground_truth.read_text())["resolved"]
    mine, crossing = build(args.corpus)

    mine_pairs = {(s, t) for s, d in mine.items() for t in d}
    truth_pairs = {(s, t) for s, d in truth.items() for t in d}
    agreed = mine_pairs & truth_pairs

    miscounted = [
        (s, t, n, truth[s][t])
        for s, d in mine.items()
        for t, n in d.items()
        if t in truth.get(s, {}) and truth[s][t] != n
    ]

    print(f"sources          mine {len(mine):>5}   obsidian {len(truth):>5}")
    print(f"distinct pairs   mine {len(mine_pairs):>5}   obsidian {len(truth_pairs):>5}")
    pct = len(agreed) / len(truth_pairs) if truth_pairs else 0.0
    print(f"  agreeing            {len(agreed):>5}   ({pct:.1%} of obsidian)")
    print(f"  mine only           {len(mine_pairs - truth_pairs):>5}")
    print(f"  obsidian only       {len(truth_pairs - mine_pairs):>5}")
    print(f"  same pair, count differs  {len(miscounted):>5}")
    print(f"cross-boundary links dropped by both      {crossing:>5}")

    for label, pairs in (
        ("mine only", sorted(mine_pairs - truth_pairs)),
        ("obsidian only", sorted(truth_pairs - mine_pairs)),
    ):
        if not pairs:
            continue
        print(f"\n{label}, first {min(args.show, len(pairs))} of {len(pairs)}:")
        for source, target in pairs[: args.show]:
            print(f"  {source}  ->  {target}")

    if miscounted:
        shown = min(args.show, len(miscounted))
        print(f"\ncount disagreements, first {shown} of {len(miscounted)}:")
        for source, target, mine_n, truth_n in sorted(miscounted)[: args.show]:
            print(f"  mine {mine_n} / obsidian {truth_n}   {source}  ->  {target}")

    disagreements = len(mine_pairs ^ truth_pairs) + len(miscounted)
    print(f"\n{disagreements} disagreement(s).")
    print("Every one needs a named cause before this is trusted.")
    return 1 if disagreements else 0


if __name__ == "__main__":
    sys.exit(main())
