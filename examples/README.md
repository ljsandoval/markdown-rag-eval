# Example Corpus

A small synthetic markdown corpus under `corpus/`. It has one job: **prove the code runs.** Fourteen notes, deterministic, shipped publicly so anyone who clones this repo can reproduce the demo exactly.

**This is example data, not a test fixture.** The module test suite asserts module behaviour and does not assert the shape of these notes; test inputs live in `tests/fixtures/` and are free to be minimal and artificial. The distinction, and why it had to be made, is ADR 0007.

It is **not** the corpus the headline numbers come from. A recall figure measured over notes and questions written by the same person is close to circular: it demonstrates that the pipeline executes, not that retrieval works on real text. The reported numbers come from a private 698-note corpus and are labelled unreproducible, with the reason stated. See the project README.

> [!warning] Frozen once a published number depends on it
> The demo numbers in the project README are measured against this corpus, so editing a note silently invalidates them. **Change it only with a deliberate reason**, and re-measure anything published.
>
> Nothing in the test suite will stop you. What catches it instead is provenance: every results file records a `corpus_hash`, so a number measured against a corpus that has since changed is detectable from the artifact rather than from anyone remembering to run something.

## The subject matter is invented

A fictional outfit called Meridian Tidal, which runs a network of tide gauge stations and ingests water level observations. Every station, person, incident and identifier in here is made up. The domain was chosen because it produces the shapes a real technical knowledge base has — runbooks, decision records, a glossary, an incident writeup, meeting notes — with cross-references that are genuinely meaningful rather than decorative.

## Layout

```
corpus/
  projects/     tide-gauge-ingest, sensor-backfill
  decisions/    postgres-for-observations, retire-the-kafka-tier
  runbooks/     restart-the-collector, recover-a-data-gap
  reference/    glossary, station-metadata-schema, quality-flags, data-retention-policy
  incidents/    collector-outage-2027-03-14
  notes/        weekly-sync-2027-03-18
  people/       avery-lin, jun-okafor
```

14 notes, 44 wikilinks, every link resolving to a note that exists. Frontmatter on all of them carries `tags` and `area`.

## Deliberate properties

Each row is a case something in the pipeline has to handle, and the reason this corpus looks the way it does.

**These are not a substitute for test inputs.** This corpus covers the chunker's structural cases because they occur naturally in real notes. It covers almost none of the wikilink cases — it has no embeds, no path-form targets, no frontmatter links, nothing inside code spans, no ambiguous or unresolved targets — because a corpus that did would stop reading as a credible knowledge base. Those cases are exercised from `tests/fixtures/` instead.

| Property | Where | Why it is here |
|---|---|---|
| `##` comment line inside a fenced code block | `runbooks/restart-the-collector.md` | The chunker must not treat it as a heading. This is the case a naive splitter gets wrong. |
| Wide markdown table, 10 rows | `reference/station-metadata-schema.md` | Must emerge in exactly one chunk. |
| Mermaid fence | `reference/data-retention-policy.md` | Must emerge in exactly one chunk. |
| Four-level-deep heading (`####` under `###` under `##`) | `runbooks/recover-a-data-gap.md` | Exercises `breadcrumb` with three enclosing headings. |
| Content before the first heading | `notes/weekly-sync-2027-03-18.md` | Produces the `heading = None` preamble chunk. |
| Nine very short sections, one or two lines each | `reference/glossary.md` | The chunk-size **floor** case. Thin chunks carry little signal and rank almost randomly. |
| One 2,200-character section, roughly 550 tokens | `incidents/collector-outage-2027-03-14.md` | The chunk-size **ceiling** case. It exceeds a 512-token model's max sequence length, so it is the note that makes silent truncation visible. |
| A note excluded by path | `people/`, via `corpus/.mdragignore` | Exercises the exclusion mechanism publicly, without needing the private corpus's rules. The ignore file is part of the corpus: exclusions are declared by the corpus, not by the tool. |

## Question kinds the corpus supports

The eval set for this corpus lives in `../eval/fixture.yaml`. The corpus was built so each question kind has somewhere real to point.

**Direct.** Most notes answer something plainly. "How often does the collector poll?" is answered in one section of `tide-gauge-ingest`.

**Vocabulary mismatch.** `reference/quality-flags.md` describes untrustworthy readings **without using the words** trust, trustworthy, reliable, or bad — it says *suspect*, *flag 3*, *failed the range check*. So "how do I tell whether a reading can be trusted?" shares no useful vocabulary with the answer. BM25 should score near zero here; if it does well, the question is not actually mismatched and needs rewriting.

**Multi-hop.** "Why does the ingest pipeline write straight to Postgres instead of going through a queue?" needs **two** notes: `decisions/retire-the-kafka-tier.md` holds the rationale, `projects/tide-gauge-ingest.md` holds the current shape. Neither answers it alone, which is why these questions use `require: all`. A second pair: the consequences of the 24-hour-retention stations span `incidents/collector-outage-2027-03-14.md` and `reference/data-retention-policy.md`.

**Unanswerable.** Deliberately absent subject matter, so refusal behaviour has real cases in Phase 2. The corpus says nothing about billing or pricing, authentication or access control, mobile applications, deployment and CI, or anything about the public API beyond which aggregate tier it reads. Questions on any of those should be refused, not answered.

## Dangling threads, left in on purpose

Real knowledge bases contain unresolved work, and retrieval over a corpus of tidy conclusions is an easier problem than the real one. So: the write-recency monitoring check is named as the highest-value missing piece in two notes and does not exist; the per-station backfill batch mode is agreed in the sync note and never scheduled; and the collector's inability to distinguish a station that never reported from one that stopped is recorded as a known limitation with no owner.

These also give the eval somewhere to go for questions whose honest answer is "the corpus says it is not done."

## Validating it

Nothing validates it automatically, by design. A test asserting the shape of example data would not be testing the module — see ADR 0007, which deleted exactly that test.

Two things are still true of this corpus and worth preserving by hand if it is ever edited: every note carries `tags`, and **every wikilink resolves to a note that exists**. The second matters more than it looks — a dead link here would weaken the graph-expansion experiment in Phase 3, and the failure would present as a negative result rather than as a broken corpus. That is a property of this corpus being a good example, not a property the software requires; the software must tolerate unresolved links, because 17.5% of the real corpus is deliberate forward references.
