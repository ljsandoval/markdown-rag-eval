---
status: accepted
date: 2026-10-15
---

# 0005. How wikilinks are modelled and resolved

## Context

A wikilink `[[Some Note]]` is a reference from one note to another. The link graph is the input to a planned retrieval experiment: after vector search, pull in chunks from notes the top hits link to, and re-rank. Resolution quality is therefore a **confound on that experiment's result** — under-resolving makes a negative result uninterpretable, and over-resolving pulls in irrelevant chunks and makes the idea look worse than it is.

The earlier spec said how to *extract* a link and nothing about how the extracted text becomes a file. Everything below was measured against the target corpus on 2026-10-15 (655 notes, 3,510 wikilinks) rather than argued, which is why several candidate rules were dropped outright.

| Question | Measured | Consequence |
|---|---|---|
| Links in frontmatter | **796, 22.6% of all links** | Must be captured; drives the main decision below |
| Links inside inline code spans | **108** | Must be skipped |
| Links inside fenced code blocks | 49 | Must be skipped |
| Links needing case-insensitive matching | **0** | Do not implement case folding |
| Notes declaring `aliases:` | **0** | Do not implement alias resolution |
| Markdown-style links resolving to a note | **0** of 2 local | Do not support them |
| Targets with nested brackets | **0** | Do not handle |
| Embeds targeting attachments, not notes | **24** of 33 | Attachments are not graph edges |
| Path-form targets containing `/` | 75 | Use the path when present |
| Ambiguous targets, 2+ candidate files | 12, 0.4% | Record, never silently pick |
| Unresolved targets | 615, 17.5% | Tolerated, not an error |

## Decision

**Frontmatter links are carried at note level, separate from chunks.** A chunk's `wikilinks` holds only links found in that chunk's own text. Frontmatter links belong to the note and are stored once per note.

**Resolution is case-sensitive**, by basename, after taking the final path segment and stripping a trailing `.md`.

**Unresolved and ambiguous targets are recorded, never guessed at.** An unresolved target is normal and is not an error — except in the fixture corpus, where the integrity test asserts every link resolves.

## Why frontmatter links sit at note level

22.6% of the graph is in frontmatter — overwhelmingly `Area:`, plus `Links:`, `role:` and `related_area:`. The chunking rules strip frontmatter before splitting, so a chunk-level link field would have discarded all of it silently. A quarter of the edges missing would make the retrieval experiment's result meaningless either way it came out.

The alternative is replicating a note's frontmatter links onto each of its chunks. That stores the same information, so the choice is not about capability. It is about **double counting on aggregation**: asking "which notes does this retrieved set link to" over chunk-level links counts a note's `Area:` edge once per retrieved chunk rather than once, and the inflation scales with note length, since longer notes yield more chunks. That is a bias proportional to something irrelevant, and it would be invisible in the output.

Note-level storage makes counting once the default. A per-chunk field with a documented dedupe step would also work — the spec and a test are a real mechanism, not a reminder — but it makes the correct thing require an extra step rather than making the wrong thing hard to express.

**This has no effect on embeddings.** Only `chunk.text` is embedded, frontmatter is stripped before chunking, and link metadata is carried alongside the vector rather than inside it. Every vector in the index is identical under either option. The decision is about the shape of metadata used after retrieval.

## Why case-sensitive

Zero links in the corpus need case folding, so case-insensitive matching buys nothing measurable. It also costs something real: the corpus is synchronised to a Linux host, where the filesystem is case-sensitive. Case-insensitive resolution would behave differently on each machine, so a link that worked on one would silently fail on the other. Case-sensitive matching fails identically everywhere, which is the property worth having.

## Consequences

- The link graph has two sources per note, and anything consuming it must take the union of a note's frontmatter links and its chunks' links. That is the cost of the decision and it is deliberate.
- Attachment embeds are excluded, so image and audio references do not appear as edges. 24 of 33 embeds are attachments, so including them would have been mostly noise.
- An embed of a note **is** an edge, and carries a flag distinguishing it from a plain link. Obsidian models `links` and `embeds` separately; whether a transclusion is a stronger edge for retrieval is left as a measurable question.
- Ambiguous targets resolve to **all** candidates, with the count reported. At 0.4% this cannot move a result, and reporting it lets any finding be caveated honestly.
- The implementation is validated against ground truth exported from Obsidian's own `app.metadataCache.resolvedLinks`, which is the authoritative resolver. Agreement with a third-party reimplementation would prove less.

## Alternatives rejected

**Obsidian-faithful resolution** — absolute vault path, then relative to the linking note, then basename with proximity preference. Correct, and more than this corpus needs: the only case where proximity matters is the 12 ambiguous links, and resolving those to all candidates handles them without the machinery.

**Merging frontmatter links into each chunk's single link list.** Loses provenance. A categorical `Area:` edge and a referential in-prose mention are plausibly different strengths for graph expansion, and merged they cannot be told apart or tested separately.

**`obsidiantools` as a runtime dependency.** It builds a NetworkX graph of a vault and supports shortest-path links. Rejected for the same reason a retrieval framework was: writing the resolution is the demonstrable work, and a library hides exactly the mechanics being shown. It remains useful as a cross-check, though a reimplementation is a weaker oracle than Obsidian itself.
