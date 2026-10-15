---
status: current
phase: 1
---


# Vault RAG - Phase 1 Specification

> [!note] This document is the contract for Phase 1
> It states decisions rather than arguing them. The reasoning behind each one lives in private
> design notes outside this repo; where a decision was contested, there is an ADR in `docs/adr/`.
>
> **It is amended by commit.** If the build proves a statement here wrong, change it in the same
> pull request as the code that proved it, and say why in the issue comment. A spec that disagrees
> with the code is the failure this layout exists to prevent.

## Scope

Build and measure **retrieval only**. No model calls, no generation, no answers. The phase produces a defensible retrieval number for an embedding pipeline and a keyword baseline over the same question set.

| In scope                                                                                 | Out of scope                                                                 |
| ---------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| Corpus loading, heading-aware chunking, metadata extraction                              | Generation, prompting, citations (Phase 2)                                   |
| Path exclusions, enforced by test                                                        | LLM grading, refusal cases (Phase 2)                                         |
| Local embeddings, cosine top-k retrieval                                                 | Re-ranking, graph expansion (Phase 3)                                        |
| BM25 keyword baseline                                                                    | Chat UI, vault write-back, bot integration (never)                           |
| Eval set, recall metrics, per-question results                                           | Chunk floor/ceiling tuning (own task, after the histogram exists)            |
| **Runs against both the fixture and the private vault**, the vault being the deliverable | Query logging and organic usage measurement (Phase 2, and then elapsed time) |

**Terms:** RAG, embedding, chunk, eval, recall@k and BM25 are defined in the proposal's Terms table. One term is new here: a **breadcrumb** is the ordered list of enclosing headings for a chunk, e.g. `["Runbook", "If the collector will not start"]`.

---

## Package layout

```
src/mdrag/
    __init__.py
    corpus.py      # discover and load markdown files, parse frontmatter
    chunker.py     # heading-aware splitting
    embed.py       # model load, prefix handling, batch encode, L2 normalize
    index.py       # build and load the on-disk array
    retrieve.py    # cosine top-k
    baseline.py    # BM25
    evalset.py     # load and validate the eval set
    metrics.py     # recall, rank, MRR
    cli.py         # the two commands
fixtures/corpus/   # the fixture corpus, shipped and public
eval/
    fixture.yaml   # eval set for the fixture corpus, public
    private/       # vault eval set, gitignored, lives in the private mirror
```

One module per concern, each independently testable. `retrieve.py` must not import `chunker.py` - it consumes an index, not a corpus.

**Prerequisite:** `README.md` must exist at the repo root before `uv sync` will work at all. `pyproject.toml` names it in the `readme` field, and hatchling refuses to build the package without the file existing - this is a build prerequisite, not a documentation nicety.

## Data shapes

Pydantic models, so validation errors surface at the boundary rather than as a `KeyError` three calls later.

```python
class Chunk(BaseModel):
    note_path: str          # corpus-relative, POSIX separators, e.g. "reference/glossary.md"
    heading: str | None     # the chunk's own heading text; None for pre-heading preamble
    heading_level: int | None
    breadcrumb: list[str]   # enclosing headings, outermost first, excluding own heading
    text: str               # heading line included, verbatim from source
    char_start: int         # offset into the post-frontmatter body
    char_end: int
    tags: list[str]         # from frontmatter
    area: str | None        # from frontmatter
    wikilinks: list[str]    # outbound [[targets]] found in this chunk's text
    char_count: int

class EvalQuestion(BaseModel):
    id: str                   # stable, e.g. "q007"
    question: str
    expected_notes: list[str] # corpus-relative paths; empty only when kind == "unanswerable"
    expected_heading: str | None
    require: Literal["any", "all"] = "any"
    kind: Literal["direct", "vocabulary-mismatch", "multi-hop", "unanswerable"]
    holdout: bool = False
```

`char_start`/`char_end` exist so a retrieved chunk can be traced back to its exact source span. That is what makes a failure analysis possible rather than speculative.

## Corpus contract

A corpus is **a directory containing `.md` files**, nothing more. No Obsidian assumptions, no required folder names, no vault coupling.

- Discover `**/*.md` under the corpus root, excluding configured paths.
- Frontmatter parsed with `python-frontmatter`. **A missing or malformed frontmatter block is not an error** - tags and area become empty. A corpus is allowed to be plain markdown.
- `note_path` is always relative to the corpus root with forward slashes, on every platform.
- Files are read as UTF-8; a decode failure names the file and aborts the run rather than skipping silently.

### Exclusions

**Exclusions are declared by the corpus, in a `.mdragignore` file at the corpus root.** Not by tool configuration and not hardcoded anywhere.

This follows from ADR 0003: which notes must not be indexed is a fact about a particular corpus, so a tool carrying that list would know something about a specific private collection and stop being corpus-agnostic. The corpus brings its own rules; the tool reads them.

**Format**, deliberately smaller than gitignore's:

- One pattern per line, matched against the corpus-relative POSIX path.
- A trailing `/` means a directory and everything under it. Otherwise the pattern is matched as a glob, with `*` not crossing `/` and `**` crossing any number of segments.
- Blank lines ignored. A line beginning with `#` is a comment.
- **No negation, no re-inclusion.** An exclusion that can be undone later in the file is how a private note gets indexed by accident.
- A missing `.mdragignore` means no exclusions, which is correct for a corpus that has nothing to hide.

`--exclude PATTERN` on the command line **adds to** the file rather than replacing it, for ad-hoc runs. There is no flag to disable the file.

The fixture corpus ships a `.mdragignore` containing `people/`, which is how the mechanism is exercised publicly without needing the private corpus's rules.

**Exclusion happens at discovery**, so an excluded file is never opened, never embedded, and cannot reach a results file. This is enforced by test, not by convention - see the test inventory.

> [!warning] A missing ignore file is silent, and that is the one real risk here
> If `.mdragignore` is absent, renamed, or has a typo'd pattern, the run proceeds and indexes everything. Nothing errors, because an empty exclusion list is legitimate.
>
> The mitigation is **visibility rather than a guess about intent**: every run records the patterns it actually applied and the file it read them from, in the results `run` block. A run that excluded nothing is then obvious in its own output, and a published number can be checked against what it indexed. Do not try to infer that a corpus "should" have exclusions - that is corpus knowledge, and it belongs in the corpus.

## Chunking rules

Split at ATX headings. The rules exist because each one has a failure case in the fixture corpus:

1. **Frontmatter is stripped before chunking** and never appears in chunk text.
2. **Split at any line matching `^#{1,6}\s`** - a flat split at every heading level, not a hierarchical one. Hierarchy is preserved in `breadcrumb`, not in nesting.
3. **Never split inside a fenced code block.** Track fence state across ``` and ~~~ openers, honor the longer-fence rule, and treat a `## comment` line inside a fence as text. The fixture's `runbooks/restart-the-collector.md` contains exactly this.
4. **Content before the first heading becomes one chunk** with `heading = None`.
5. **Tables and Mermaid blocks are never split**, which follows from rules 2 and 3 - neither contains a heading line - but the fixture asserts it directly because it is the rule most likely to break under a future refactor.
6. **No floor, no ceiling in this phase.** Chunks are emitted at whatever size the headings imply. Instead, the index build **writes a chunk-length histogram**, which is the input to the floor/ceiling decision. Do not guess those bounds before the histogram exists. **The ceiling is not purely a tuning knob.** Small embedding models cap at 256 or 512 tokens and **silently truncate** past it, so a long chunk produces an ordinary-looking vector representing only its opening. The ceiling therefore has to be derived from the chosen model's max sequence length. The index build **must log how many chunks exceed it**, which makes the truncation visible instead of invisible. See the private reference notes on embeddings.
7. `wikilinks` are extracted per chunk. The rules are their own section below, because there are more of them than a chunking rule should carry.

## Embedding model

### Library and constraints

`sentence-transformers`, running locally on CPU. No hosted embedding API: Anthropic serves no embeddings endpoint, and any other vendor means sending a private corpus to a third party, which the two-corpus design exists to avoid. Reasoning in the private reference notes on embeddings.

Three hard gates. A model failing any of them is not a candidate:

- Runs locally, CPU-only, no network at query time after the first download.
- Permissively licensed. The repo is public.
- Small enough that a full index build over roughly 6,000 chunks finishes in minutes, not hours.

### Candidates

Compare **two or three, not more** - the reason is in the next subsection. Properties below are from memory and **must be verified against each model card before use**; `dimensions` and `max_seq_length` are both readable from the loaded model and the code reads them rather than trusting this table.

| Model | Dims | Max tokens | Prefix required | Why it is a candidate |
|---|---|---|---|---|
| `sentence-transformers/all-MiniLM-L6-v2` | 384 | ~256 | No | The ubiquitous baseline. Its short ceiling is a feature here: it measures what truncation costs. |
| `BAAI/bge-small-en-v1.5` | 384 | ~512 | **Yes, on queries** | Same storage cost, twice the ceiling, strong on retrieval benchmarks. |
| `intfloat/e5-small-v2` | 384 | ~512 | **Yes, both sides** | Alternative to bge at the same size, trained explicitly for asymmetric search. |

A 768-dimension model (`all-mpnet-base-v2`) is a fallback only if all three above fail the bar. At this corpus size the extra storage and compare cost is irrelevant, so the reason to prefer small is build time, not query time.

### What 25 questions can and cannot decide

The eval cannot rank these models finely. At an observed recall of 0.70 over 25 questions the 95% interval is roughly 0.52 to 0.88, so two models four points apart are indistinguishable. See the private reference notes on eval design.

So the selection criterion is **not** "which scores highest." It is:

> **Pick the model that clears a usable bar with the fewest operational complications.**

Ranked, with the first as a gate and the rest as tiebreakers in order:

1. **Clears the bar**: note-level recall@5 materially above the BM25 baseline. If no candidate does, that is the finding and it goes in the failure analysis rather than being tuned away.
2. **No prefix requirement**, or one that is impossible to forget because it lives in the model config rather than in call sites.
3. **Shorter index build time.**
4. **Smaller on disk.**

Report every candidate's numbers. Do not report a winner by recall alone when the intervals overlap - say they tied and explain which tiebreaker decided it.

### The prefix trap

Some models expect an instruction prefix and are **measurably worse without it, with no error and no warning.** `bge` wants a prefix on the query only; `e5` wants `query:` and `passage:` on their respective sides. Getting this wrong looks exactly like the model being mediocre.

Therefore the prefix convention is **a property of the model, carried in config, applied inside `embed.py`** - never a string a caller remembers to prepend. Two consequences for the contract below: the prefix pair is recorded in the index metadata alongside the model id, and a test asserts that embedding the same text through the query path and the passage path produces different vectors for a model that declares prefixes.

### The `embed.py` contract

- Reads `max_seq_length` and the embedding dimension **from the loaded model**. Neither is hardcoded anywhere.
- Exposes two entry points, `embed_passages()` and `embed_query()`, so the prefix asymmetry is structural rather than a flag.
- **L2-normalizes every vector**, so cosine similarity is a dot product. Asserts unit length within tolerance on a sample.
- Batches, with the batch size a parameter.
- Counts and reports inputs whose token length exceeds `max_seq_length`, feeding acceptance criterion 8.

### Reproducibility

Recording a model id is not sufficient: a HuggingFace repo can be updated in place, so the same id can mean different weights months apart. The index metadata records, and the results file carries forward:

| Field | Why |
|---|---|
| `model_id` | Which model |
| `model_revision` | The pinned commit hash. **A number measured against an unpinned model is not re-derivable.** |
| `dimensions`, `max_seq_length` | Read from the model, not assumed |
| `normalized` | Always true, recorded so a future change is visible |
| `query_prefix`, `passage_prefix` | The convention actually used, including empty strings |

The index load aborts on a mismatch of `model_id` **or** `model_revision` against what is requested, for the reason in the Retrieval section: the arithmetic still works and the rankings are quietly wrong.

First run downloads the model to the local cache; every later run is offline. The index build must not require the network once the cache is warm, and a test with the network unavailable is the honest way to know that.

## Wikilink extraction and resolution

Decisions and the measurements behind them are in ADR 0005. This states the mechanics.

### Extraction

Match `(!?)\[\[([^\]]+)\]\]`, capturing the embed marker and the full inner text. Then split the inner text on the first `|` (alias) and the first `#` (heading or block subpath), keeping the part before both.

Skip, in this order, before matching:

1. **Fenced code blocks.** Reuse the chunker's fence state rather than re-deriving it.
2. **Inline code spans** - text between single backticks. **108 wikilinks in the target corpus sit inside these**, more than the 49 inside fenced blocks, so missing this is the larger error.

Then normalize the target: strip surrounding whitespace, take the final `/`-separated segment, and strip a trailing `.md`.

Not supported, each because the corpus contains none: alias resolution via frontmatter `aliases:`, markdown-style `[text](note.md)` links, and targets containing nested brackets. If a future corpus needs them, measure first.

### Resolution

1. If the target contained a `/`, try the full relative path against the corpus first.
2. Otherwise, and as fallback, match the final segment against note basenames, **case-sensitively**.
3. More than one candidate is **ambiguous**: resolve to all of them and count it.
4. No candidate is **unresolved**: record it and carry on. This is normal, not an error.

### Where links live

| Source | Stored on | Why |
|---|---|---|
| A chunk's own text | That chunk's `wikilinks` | It is that passage's reference |
| The note's frontmatter | **The note, once** | 22.6% of the graph; replicating it per chunk double-counts on aggregation. ADR 0005. |

Each entry carries whether it was an **embed** (`![[...]]`) or a plain link. An embed whose target has a non-markdown extension - image, audio, pdf - is **not an edge** and is not recorded; 24 of 33 embeds in the target corpus are attachments.

Anything consuming the graph takes the union of a note's frontmatter links and its chunks' links.

### Validation

The implementation is checked against ground truth exported from Obsidian's own `app.metadataCache.resolvedLinks`, which is the authoritative resolver. A one-off export is enough; this is a correctness check, not a runtime dependency.

Expect disagreements in both directions and treat each as a finding rather than a bug to suppress: Obsidian resolves ambiguity by proximity where this does not, and Obsidian counts frontmatter links that an earlier version of these rules would have dropped.

## Retrieval

```python
def retrieve(question: str, k: int) -> list[Chunk]: ...
```

1. Embed the question through `embed_query()`, with **the same model and revision** recorded in the index metadata. If either differs from what the index declares, **abort with an error.** A silent mismatch produces plausible nonsense rankings and is the single worst failure mode available here.
2. Cosine similarity against every chunk. Vectors are L2-normalized at index time, so this is one `numpy` dot product over the whole array.
3. Sort descending and return the top k with scores.

**Deterministic tie-breaking is required:** sort by score descending, then `note_path` ascending, then `char_start` ascending. Without it, equal scores order by array position and the "same question twice" test becomes flaky rather than failing honestly.

**No vector database.** About 6,000 chunks at 384 dimensions is a 9 MB array; one matrix multiply scores all of it in under a millisecond. The index is a `.npy` file plus a JSON sidecar holding chunk metadata and the embedding model id. Both are gitignored build artifacts, rebuildable from the corpus.

> [!info] Background
> The mechanics - what an embedding is, why cosine rather than Euclidean distance, why normalizing turns it into a dot product, and the seven ways embedding retrieval fails - are in the private reference notes on embeddings.

## Baseline

BM25 over the same chunks, same `retrieve` signature, so the eval runner treats the two systems identically.

Specified exactly, because a baseline that cannot be reproduced is not a baseline:

- Tokenization: lowercase, split on `[^a-z0-9]+`, drop empty tokens. **No stemming, no stop words** in this phase - both are tunable knobs and the point is a fixed reference.
- Parameters `k1 = 1.5`, `b = 0.75`, the standard defaults.
- Same deterministic tie-breaking.

> [!info] Background
> The formula term by term, what `k1` and `b` actually do, a worked example, and why BM25 is expected to score near zero on the vocabulary-mismatch questions are in the private reference notes on BM25.

## Metrics

Let `Q` be the answerable questions - `kind != "unanswerable"`. Unanswerable questions carry no expected notes and are **excluded from every recall number** here; they are scored in Phase 2 against refusal behavior. The results file records how many were skipped, so the denominator is never ambiguous.

For one question `q` and the ranked chunk list:

| Metric | Definition |
|---|---|
| `chunk_recall@k` | Hit if any of the **top k chunks** belongs to an expected note. Reported, not headline - several chunks of one long note fill the slots, so it overstates how many candidates were really tested. |
| **`note_recall@k`** | Dedupe the **full ranked list** by `note_path`, keeping first occurrence, take the first k distinct notes, hit if expectations are met. **The headline metric.** |
| `exact_chunk_recall@k` | Hit if a top-k chunk has both an expected `note_path` and the `expected_heading`. Skipped for questions with no `expected_heading`. |
| `first_correct_rank` | 1-based position of the first chunk from an expected note; `null` on a miss. |
| `mrr` | Mean of `1 / first_correct_rank`, contributing 0 for a miss. |

`require: "any"` means one expected note suffices. `require: "all"` means every expected note must be present - this is what makes a multi-hop question honest, and it is why the field exists rather than being inferred from list length.

Report `k = 1, 3, 5, 10` for all three recall variants. The curve costs nothing once the list is sorted and separates two failures a single number conflates: high `@10` with low `@1` is a ranking problem; low `@10` is a chunking or embedding problem.

**An expected note that does not exist in the corpus, or that an exclusion removed, is an eval set error and must abort the run** with the question id and the path. A silently-impossible question depresses the score forever and is nearly undetectable by reading the number.

### How precisely 25 questions can be read

At an observed recall of 0.70 over 25 questions the standard error is about 0.09, so the 95% interval runs roughly **0.52 to 0.88**. Two consequences that bind on how results get reported:

- **Large differences are real; small ones are not.** Embeddings at 0.70 against BM25 at 0.40 is a finding. 0.70 against 0.75 is a tie, and calling it a win would be overreading.
- **The interval goes in the README and the failure analysis**, not just in a footnote. Quoting a three-significant-figure recall from 25 questions as though it were precise is exactly what someone who does this work will catch.

Reasoning in the private reference notes on eval design.

## Eval set format

```yaml
version: 1
corpus: fixture
questions:
  - id: q001
    question: "How do I tell whether a reading can be trusted?"
    expected_notes: ["reference/quality-flags.md"]
    expected_heading: "Flag values"
    kind: vocabulary-mismatch
    holdout: false
```

Rules, from the proposal and binding here:

- **25 questions for the vault eval set**, committed before any retrieval result is seen.
- **10 marked `holdout: true`**, not looked at until Phase 3. The runner prints train and holdout scores separately and **defaults to train only**; holdout requires an explicit `--holdout` flag, so it cannot be tuned against by accident.
- Composition must include: at least 3 `vocabulary-mismatch`, at least 2 `multi-hop` with `require: all`, and at least 3 `unanswerable`.
- The fixture eval set is smaller - 8 to 10 questions - and exists to prove the harness runs, not to produce a headline number.
> [!info] Background
> What an eval is, the three families of grading, why retrieval is measured separately from generation, and **what `multi-hop` means and why it uses `require: all`** are in the private reference notes on eval design. The short version of the multi-hop rule: a multi-hop question's answer exists in **no single note** and must be assembled from two or more, which tests whether retrieval surfaces a complementary *set* rather than k near-duplicates of one strong match. Under `require: "any"` it would score a hit on one note and test nothing extra, so `all` is what makes the measurement match the claim. Expect it to be the worst number in the report - it is the case Phase 3 exists to improve.

## The two runs, and which one is the point

The fixture corpus takes up most of this document because it had to be specified. That is a property of the writing, not of the phase. **The vault run is the deliverable.** Stated plainly so the emphasis is not mistaken:

| | Fixture corpus | Private vault |
|---|---|---|
| Size | 14 notes | ~698 notes, ~600k words |
| Eval set | 8 to 10 questions | **25 questions, 10 held out** |
| Job | Prove the code runs; let anyone reproduce the demo | **Produce the numbers that get discussed** |
| Reproducible by others | Yes | No, and labelled as such |
| Where results live | Public repo | Private repo |

A number measured on notes and questions written by the same person is close to circular, which is why the fixture deliberately does not produce the headline. Reasoning in the private design notes.

### Characterization, which needs no ground truth at all

The index build over the vault produces a set of numbers that are **not an eval** and cost no labeling effort: chunk count, the length histogram, how many chunks exceed `max_seq_length`, token totals, and build time.

This output deserves naming as a deliverable in its own right, because it is likely the most useful thing the phase produces for discussion. A statement like *"600,000 words across 698 notes became roughly 6,000 chunks, and some fraction of them exceed the embedding model's context window and are silently truncated"* is a concrete defect found by measurement on a real corpus. It needs no ground truth, so it cannot be argued with on eval-design grounds, and it reads as engineering rather than as a score.

Record it for the vault, not only for the fixture. The truncation count in particular is the input to the chunk-ceiling decision and the evidence behind it.

### Deferred: contextual metadata in the embedded text

Only `chunk.text` is embedded, so a chunk carries no signal about which note or area it came from. A known technique prepends that context before embedding:

```
Area: Career. Note: Resume Workshop - Panel Results. Section: Summary rewrites.
<chunk text>
```

This is plausibly a large win on a corpus where a passage's meaning depends on the note it sits in, and it is **deliberately not done in Phase 1**: it changes every vector in the index, so doing it now would mean the baseline and the experiment move together and neither is measurable.

Recorded as a Phase 3 candidate alongside graph expansion and cross-encoder re-ranking. It is testable against the same eval, which is the only reason to defer it rather than decide it.

### What this phase deliberately cannot tell you

The eval measures retrieval against questions chosen because their answers exist. It says nothing about whether the tool is **useful**, since no curated set can - organic questions are not selected for being answerable.

That gap is covered by the query log and the usage practice in the proposal, both of which depend on Phase 2. It is named here so the Phase 1 numbers are not over-read: they are a ceiling on quality, not evidence of value.

## Output artifacts

One JSON file per run, written to a path the caller names.

```json
{
  "run": {
    "timestamp": "2026-10-08T19:04:11Z",
    "code_commit": "a1b2c3d",
    "corpus_path": "fixtures/corpus",
    "corpus_file_count": 14,
    "chunk_count": 96,
    "exclude_patterns": ["people/"],
    "exclude_source": "fixtures/corpus/.mdragignore",
    "embedding_model": "<model id>",
    "system": "embedding",
    "k_values": [1, 3, 5, 10],
    "questions_total": 10,
    "questions_scored": 7,
    "questions_skipped_unanswerable": 3
  },
  "aggregate": { "note_recall": {"1": 0.57, "3": 0.71, "5": 0.86, "10": 0.86},
                 "chunk_recall": {}, "exact_chunk_recall": {}, "mrr": 0.64 },
  "per_question": [
    { "id": "q001", "kind": "vocabulary-mismatch", "hit_at": {"1": false, "5": true},
      "first_correct_rank": 4,
      "retrieved": [ {"note_path": "...", "heading": "...", "score": 0.61, "rank": 1} ] }
  ]
}
```

`per_question` is the point of the file. An aggregate alone cannot be argued with; a reader has to be able to open the failures and see what came back instead. Record the top 10 retrieved entries per question regardless of `k`.

Recording `code_commit` and `embedding_model` is what makes a number re-derivable three months later.

## CLI

```
uv run mdrag index --corpus PATH [--exclude PREFIX ...] [--model ID] --out DIR
uv run mdrag eval  --index DIR --questions PATH --system embedding|bm25|both
                   [--k 1,3,5,10] [--holdout] --out FILE
```

`index` prints the chunk count and the length histogram. `eval` prints the aggregate table and writes the JSON. Both are quiet on success beyond that - this is a measurement tool, not a progress bar.

## Acceptance criteria

Phase 1 is done when every line below is true. Each is checkable by someone other than the author, which is the actual bar: **a skeptical reader can open the eval set, disagree with it, and re-run the measurement.**

| # | Criterion |
|---|---|
| 1 | `fixtures/corpus/` holds 10 to 15 notes with the deliberate properties listed in `fixtures/README.md` |
| 2 | `eval/fixture.yaml` exists and every expected note resolves to a real file |
| 3 | The private vault eval set holds 25 questions, 10 flagged `holdout`, committed before results were seen, with the composition minimums met |
| 4 | `uv run mdrag index` and `uv run mdrag eval` both run from a clean checkout against the fixture corpus |
| 5 | A results JSON exists for the fixture corpus and for the vault, for **both** `embedding` and `bm25` |
| 6 | Aggregates report all three recall variants at k = 1, 3, 5, 10, plus MRR |
| 7 | `per_question` records the top 10 retrieved entries for every question |
| 8 | The index build emits a chunk-length histogram **and the count of chunks exceeding the model's max sequence length** |
| 8a | Index metadata and every results file record `model_id`, `model_revision`, `dimensions`, `max_seq_length`, `normalized`, and both prefixes |
| 8b | Characterization is recorded **for the vault**: note count, chunk count, length histogram, chunks over `max_seq_length`, token total, build time |
| 8c | Every results file records `exclude_patterns` and `exclude_source`, so a run that excluded nothing is visible in its own output |
| 9 | The test inventory below passes; `ruff` and `mypy` are clean |
| 10 | A written failure analysis exists, naming the mechanism behind each miss |
| 11 | `README.md` exists at the repo root: what this is, its status, how to run it against the fixture corpus, and that reported numbers come from a private corpus |

Criterion 10 is the one that converts a number into evidence of engineering, and it is the easiest to skip. It is not optional.

## Test inventory

Named here so the spec, not the implementer's mood, decides what is covered.

**Fixture corpus integrity** - these guard the fixture against drift, because a broken fixture silently invalidates every number measured against it. This test is standalone and does not go through the loader, so **the expected file count is the raw on-disk count, including excluded paths** - currently 14. Post-exclusion (what the loader actually indexes) is a different figure, currently 12, and belongs to the exclusion tests below, not this one.

- Expected file count (raw on-disk, 14) and every file parses
- Every `[[wikilink]]` in the corpus resolves to a file that exists, using the rules in "Wikilink extraction and resolution". Note that this assertion is **specific to the fixture**: an unresolved link is normal in a real corpus and is never an error there (ADR 0005)
- Every note has a frontmatter block with `tags`

**Chunker**

- A `##` line inside a fenced code block does not split a chunk
- A markdown table emerges in exactly one chunk
- A Mermaid fence emerges in exactly one chunk
- Content before the first heading becomes a `heading = None` chunk
- `breadcrumb` is correct for a three-level-deep heading
- `char_start`/`char_end` slice the source body back to the chunk text exactly
- Frontmatter keys never appear in any chunk's text

**Wikilinks**

- A wikilink inside a fenced code block is not extracted
- A wikilink inside an inline code span is not extracted
- `[[note|alias]]` and `[[note#heading]]` both yield `note`
- A trailing `.md` and surrounding whitespace are stripped
- A path-form target resolves by full path when it exists, by basename otherwise
- Resolution is case-sensitive: `[[glossary]]` does not match `Glossary.md`
- An ambiguous target resolves to every candidate and is counted as ambiguous
- An unresolved target is recorded and does not raise
- `![[note]]` is an edge and is flagged as an embed; `![[image.png]]` is not an edge
- Frontmatter links appear once per note, **not** once per chunk

**Exclusions**

- Patterns parse: directory form, glob form, comments, blank lines
- A line attempting negation is rejected rather than silently ignored
- With the fixture's `.mdragignore` in place, no chunk has a `note_path` under `people/`
- The excluded files are never opened (assert via a read counter or a monkeypatched loader)
- A corpus with no `.mdragignore` loads with zero exclusions and does not raise
- `--exclude` adds to the file's patterns rather than replacing them

**Retrieval**

- The same question twice returns an identical ranking, including ties
- An index built with model A and queried with model B aborts
- An index built at revision X and queried at revision Y aborts
- Vectors are unit length within tolerance
- For a model declaring prefixes, the query path and the passage path produce different vectors for identical input
- `max_seq_length` and dimension come from the loaded model, not a constant
- `k` larger than the chunk count returns everything without error

**Metrics**

- Hand-computed recall on a fixture of 4 questions and a known ranking
- `require: "all"` fails when only one of two expected notes is retrieved
- Unanswerable questions are excluded from the denominator
- An expected note missing from the corpus aborts with the question id

**Baseline**

- BM25 scores are reproducible across runs on identical input

## Open questions for the implementer

Two, both decided by measurement rather than in advance. Record the answer in the results file, not in prose.

- **Which embedding model.** Candidates, gates and tiebreakers are specified above; what is open is only the outcome. Run two or three, report all of them, and expect the recall intervals to overlap - the decision will likely come down to the prefix and build-time tiebreakers rather than to recall.
- **Chunk floor and ceiling.** Blocked on the histogram from criterion 8. A separate task, not part of Phase 1's acceptance.

## Related documents

- `docs/adr/` - the decisions this spec embodies, with what was rejected
- the private reference notes on embeddings - how the retrieval half works
- the private reference notes on BM25 - the baseline, term by term
- the private reference notes on eval design - eval design, and what a 25-question set can and cannot resolve
- `fixtures/README.md` - the fixture corpus and its deliberate properties

Design reasoning, options considered and rejected directions live in private notes outside this
repository. Where a decision is load-bearing for the code, it is recorded as an ADR here.
