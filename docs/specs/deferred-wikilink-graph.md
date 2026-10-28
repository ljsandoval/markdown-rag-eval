# Deferred: the wikilink graph

**Status: deferred out of Phase 1 on 2026-10-28.** This is not a Phase 1 contract and nothing here gates Phase 1's acceptance criteria.

## Why this was deferred

Phase 1's deliverable is a measured comparison of embedding retrieval against a keyword baseline. Link extraction contributes nothing to it. The evidence, recorded so the reasoning survives:

- **None of Phase 1's eleven acceptance criteria mentions wikilinks.** They cover the eval set, the CLI running from a clean checkout, the results JSON, recall at k and MRR, the length histogram, model and corpus provenance, the failure analysis, and the README.
- **`Chunk.wikilinks` had exactly one consumer in the whole codebase, and it was `scripts/compare-ground-truth.py`** - the tool that validates the link graph. Nothing in `src/` read it. The only justification for the work was its own verification.
- At the time of deferral, `embed.py`, `index.py`, `retrieve.py`, `baseline.py`, `evalset.py`, `metrics.py` and `cli.py` did not exist. Nothing in the project had ever computed a vector.

The graph was always headed for Phase 3, where graph-aware reranking is the leading candidate for that phase's single experiment - still a candidate, not a decision. So this is scaffolding that arrived two phases early.

**The code stays.** `wikilinks.py` works, is tested, and costs nothing to keep. `Note.frontmatter_wikilinks` and `Chunk.wikilinks` stay populated. What stops is treating any of it as a Phase 1 obligation, gating on it, or investing further.

## What stayed in Phase 1, and why

The boundary is corpus processing versus graph:

| Stayed | Phase 1 needs it for |
|---|---|
| `corpus.py` discovery, `.mdragignore`, `parse_frontmatter` | Criterion 8b's note counts, 8c's exclusion patterns, and keeping frontmatter out of chunk text |
| `markdown.py` fence and heading scan | Chunking rule 3 - a `##` inside a fenced block is not a heading |
| `chunker.py` splitting, offsets, breadcrumb | The units that get embedded |

**One thing this work earned on Phase 1's behalf.** The comparison against Obsidian is what surfaced the malformed-frontmatter leak: 19 notes whose invalid YAML caused `corpus.py` to hand the whole frontmatter block through as body text, which would have put `tags:` into chunk text and broken a stated chunking rule. That was a real Phase 1 defect found by graph work.

## Known defects, carried forward

Two filed before the deferral, both real, neither affecting any Phase 1 criterion:

- **`resolved_by` conflates two outcomes** - the ordinary basename route for a no-slash link and the path-form rescue that actually diverges from Obsidian. This defeated the comparison's classifier. Tracked as issue #19.
- **The extraction regex swallows a real link** when prose contains a literal `[[`, because `[^\]]+` excludes `]` but not `[`. One note of 397, one link of 2,846. Tracked as issue #20, which also notes that ADR 0005's "targets containing nested brackets: 0" was measured with the broken regex and may be an artifact.

**Do not write chunk links into the index sidecar while #20 is open.** A published artifact carrying link data with a known defect, for no reader, is worse than one that omits it.

## The Obsidian ground-truth apparatus

`scripts/obsidian-export-resolved-links.js` and `scripts/compare-ground-truth.py` are deferred-scope tooling. They are not a Phase 1 gate and a nonzero exit from the comparison does not block Phase 1 work.

Unresolved when this was deferred: the export is a hand-made snapshot of a corpus that changes daily, it records no list of which notes existed, and `obsidian_version` came back `null` so there is no record of which resolver produced it. A design for pinning the comparison to a vault commit was sketched and not built. Whoever picks the graph work up should settle what role the export plays - a deliberate receipt or a standing gate - before building anything else on it.

## Why the model is shaped this way

Moved from the Phase 1 spec's Data shapes section.

`WikiLink.resolved` carries the resolution outcome in one field rather than three: empty means unresolved, one entry is the normal case, two or more is ambiguous. So "count the ambiguous links" is a filter rather than a separate structure, and nothing has to be kept in sync.

**`WikiLink` carries both `link_path` and `target` because resolution needs both.** The rule is full-path-first then basename-fallback, so a resolver has to know whether the link was written as a path, and reducing a link to its final segment destroys exactly that. Carrying only the reduced form forces the resolver to re-parse `raw` and reimplement the alias and heading split, which puts the parse rule in two places and makes a future addition - block references, say - able to drift silently into wrong resolution rather than an error. With both fields present, `raw` means only what its comment says.

**`Note` is where frontmatter links live**, per ADR 0005. A chunk's `wikilinks` holds only what is in that chunk's own text. Anything consuming the graph takes the union of a note's `frontmatter_wikilinks` and its chunks' `wikilinks` - and counts the former **once**, which is the whole reason the field is here and not on the chunk.

---

The sections below are the rules as they stood in the Phase 1 spec on 2026-10-28, moved here intact. ADR 0005 remains the record of the measurements behind them.

## Wikilink extraction and resolution

Decisions and the measurements behind them are in ADR 0005. This states the mechanics.

### Extraction

Match `(!?)\[\[([^\]]+)\]\]`, capturing the embed marker and the full inner text. Then split the inner text on the first `|` (alias) and the first `#` (heading or block subpath), keeping the part before both.

Skip, in this order, before matching:

1. **Fenced code blocks.** Use `markdown.scan(text).code_ranges` rather than re-deriving fence state here.
2. **Inline code spans** - text between single backticks. **108 wikilinks in the target corpus sit inside these**, more than the 49 inside fenced blocks, so missing this is the larger error. `markdown.scan` reports both kinds of range together, since both are skipped the same way.

Then normalize in two stages, because resolution consumes both. Strip surrounding whitespace and a trailing `.md` to get `link_path`, which keeps any `/` separators intact; `target` is then `link_path`'s final `/`-separated segment. Resolution reads these two fields and **never re-parses `raw`**.

**An empty `link_path` after the split is a same-note reference and is not an edge.** `[[#Some Heading]]` names a section of the containing note, so Obsidian resolves it to that note; recording it would add a self-edge to every note that links its own sections, which distorts anything built on the graph later. It is dropped the way an attachment embed is - not recorded, not an error.

Not supported, each because the corpus contains none: alias resolution via frontmatter `aliases:`, markdown-style `[text](note.md)` links, and targets containing nested brackets. If a future corpus needs them, measure first.

### Resolution

1. If `link_path` contains a `/`, try it as a full relative path against the corpus first.
2. Otherwise, and as fallback, match `target` against note basenames, **case-sensitively**.
3. More than one candidate is **ambiguous**: resolve to all of them and count it.
4. No candidate is **unresolved**: record it and carry on. This is normal, not an error.

**How a link resolved is recorded, not just whether.** `resolved_by` carries `path`, `basename` or `unresolved`, and `resolved_by == "unresolved"` holds exactly when `resolved` is empty.

The reason is that step 2's fallback is **deliberately more forgiving than Obsidian**, which stops when a path-form link misses. The fallback is right for retrieval - it finds the note a reader meant - but it also silently rescues links whose paths went stale, so a corpus can rot without any number moving. Recording the provenance keeps both: the graph stays dense, and a basename-fallback count in the characterization output says how much rescuing was needed. One link in the target corpus resolves this way, from a path form left behind by a folder rename.

### Where links live

Extraction for both rows is `wikilinks.py`. `corpus.py` calls it on frontmatter values and owns the `Note`; `chunker.py` calls it on chunk text and owns the `Chunk`.

| Source | Stored on | Why |
|---|---|---|
| A chunk's own text | That chunk's `wikilinks` | It is that passage's reference |
| The note's frontmatter | **The note, once** | 22.6% of the graph; replicating it per chunk double-counts on aggregation. ADR 0005. |

**A frontmatter link counts only when the property value is a link.** That means the trimmed value is exactly one wikilink, or an item of a list of them - `Area: "[[Career]]"` and a `Links:` list both count. A wikilink embedded mid-sentence in a free-text property does not: `next_action: Compare against [[Other Note]] and pick one` is prose that mentions a note, not a declared relation, which is how Obsidian treats it too. Five notes in the target corpus have such embedded links.

Each entry carries whether it was an **embed** (`![[...]]`) or a plain link. An embed whose target has a non-markdown extension - image, audio, pdf - is **not an edge** and is not recorded; 24 of 33 embeds in the target corpus are attachments.

Anything consuming the graph takes the union of a note's frontmatter links and its chunks' links.

### Validation

The implementation is checked against ground truth exported from Obsidian's own `app.metadataCache.resolvedLinks`, which is the authoritative resolver. A one-off export is enough; this is a correctness check, not a runtime dependency.

Both halves are tracked: `scripts/obsidian-export-resolved-links.js` is the console snippet that produces the export, with the procedure in its header, and `scripts/compare-ground-truth.py` performs the comparison. Neither knows anything about a particular corpus. The export itself is a measurement artifact and lives outside this repo (ADR 0008).

**Compare counts, not just pairs.** The map is keyed by source and target with a count, and a rule that double-counts one link leaves every pair intact while changing its multiplicity. The first comparison found 25 disagreeing pairs and a further **14 pairs that agreed on existence and disagreed by one on count**; reducing the ground truth to target sets would have hidden the second group entirely.

Expect disagreements in both directions and treat each as a finding rather than a bug to suppress. Three are known and intentional:

- **Ambiguity.** Obsidian resolves a multi-candidate target to one file by proximity; this resolves to all candidates and counts it. Expect a superset here.
- **The basename fallback.** Obsidian reports a path-form link that misses as unresolved; this retries on the basename. Recorded through `resolved_by` rather than removed - see Resolution above.
- **Same-note heading references.** `[[#Some Heading]]` resolves, in Obsidian, to the containing note - a self-edge. This implementation drops it at extraction instead (see Extraction above), so every such link appears as "obsidian only" in the comparison. Not visible in the first full comparison because the corpus held none at the time; three appeared once the vault grew, which is how this entry came to be written rather than guessed.

The first full comparison, 2026-10-16 against Obsidian 1.13.7, agreed on **2,231 of 2,233** resolved pairs. Every remaining disagreement traced to one of the three rules now stated above, which is the evidence those rules are stated rather than guessed.

A re-export on 2026-10-27, after #17 implemented those three rules, agreed on **2,269 of 2,272** resolved pairs by existence - that fraction is against Obsidian's side alone, so it does not by itself account for every disagreement. The comparison script's full tally is **5**: the 3 pairs Obsidian has and this does not (`2,272 - 2,269`, all three same-note heading references), the 1 pair this has and Obsidian does not (the basename fallback), and 1 further pair that both sides have but count differently (also the basename fallback, rescuing a second stale path-form link to the same target an existing body link already reached). None traced to an unstated rule.

**The comparison is expected to exit 0.** `scripts/compare-ground-truth.py` classifies each of the three divergence classes above and excludes them from the exit status; only a disagreement matching none of them fails the run. Against the 2026-10-27 export it prints 5 intentional divergences and 0 unexplained. A corpus with any of these three link shapes will always carry some nonzero count of intentional divergences - that is expected and is not a reason to treat a nonzero exit as normal; a nonzero exit means an *unexplained* disagreement appeared.

## Test inventory

Moved from the Phase 1 spec's inventory.

**Wikilinks**

- A wikilink inside a fenced code block is not extracted
- A wikilink inside an inline code span is not extracted
- `[[note|alias]]` and `[[note#heading]]` both yield `note`
- A trailing `.md` and surrounding whitespace are stripped
- `[[#Some Heading]]`, with no note name, is not recorded as a link at all
- A wikilink that is the whole value of a frontmatter property is counted; one embedded in a free-text property value is not
- A note whose frontmatter is invalid YAML yields no frontmatter links, and no frontmatter key reaches its body
- `resolved_by` is `path`, `basename` or `unresolved`, and is `unresolved` exactly when `resolved` is empty
- `link_path` keeps the path form that `target` reduces away
- A `WikiLink` constructed directly, with an empty `raw`, still resolves - resolution consumes fields, never `raw`
- A path-form target resolves by full path when it exists, by basename otherwise
- Resolution is case-sensitive: `[[glossary]]` does not match `Glossary.md`
- An ambiguous target resolves to every candidate and is counted as ambiguous
- An unresolved target is recorded and does not raise
- `![[note]]` is an edge and is flagged as an embed; `![[image.png]]` is not an edge
- Frontmatter links appear once per note, **not** once per chunk
