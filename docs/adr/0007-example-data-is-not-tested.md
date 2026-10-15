---
status: accepted
date: 2026-10-15
---

# 0007. Example data is not covered by the module test suite

## Context

`examples/corpus/` — 14 interlinked notes about an invented tide-gauge operator — was originally at `fixtures/corpus/`, and issue #1 added `tests/test_fixture_corpus_integrity.py` to assert its shape: the file count, that every note carries `tags`, that every wikilink resolves, and that no note links to itself.

That test **imported no project code.** `re`, `pathlib` and `frontmatter`, nothing from `src/mdrag/`. It would have passed identically against an empty `src/`.

Two problems became visible at once.

The directory name was carrying two incompatible jobs. An **example corpus** must look realistic, stay frozen because published numbers are measured against it, and be publishable. **Test inputs** must be minimal, free to change, and may be as artificial as the case requires. Those requirements conflict directly, and the conflict surfaced when a review found that the example corpus could exercise at most two of the ten wikilink tests the spec had specified against it — no embeds, no path-form targets, no frontmatter links, nothing inside code spans, no ambiguous or unresolved targets. The tests had been written against a corpus structurally unable to host them.

"Fixture" is also already taken: in pytest it means `@pytest.fixture`. Using it for a data directory in a Python project is ambiguous on its own terms.

## Decision

**Example data is not asserted by the module test suite.** Tests exercise module behaviour; a test that imports nothing from the module is not a test of it.

`fixtures/` becomes `examples/`. `tests/fixtures/` holds test inputs. `tests/test_fixture_corpus_integrity.py` is deleted.

## What replaces the protection it offered

The concern behind that test was real: if the example corpus drifts, every published number measured against it silently stops matching. The test was a poor guard, because it only fires when someone runs the suite.

**Provenance replaces it.** The results file already records `code_commit`, the file counts and the full model identity so that a number is re-derivable; it now also records a content hash of the corpus it measured. A stale number becomes detectable **from the artifact**, with nothing to remember and no dependency on a test having been run.

The wikilink guarantee moves where it belongs: the extractor's own tests, against inputs in `tests/fixtures/` built to exercise each rule. **Every link resolving was a property of the example, never of the software.**

## Consequences

- Nothing automatically checks that the example corpus is well-formed. Given it is frozen, that check is needed approximately never, and when it is, it is a script invoked deliberately rather than a member of the test suite.
- The test suite shrinks and every remaining test exercises module code. That is the property worth having.
- **This supersedes one consequence in ADR 0005**, which reads "except in the fixture corpus, where the integrity test asserts every link resolves." That test no longer exists. ADR 0005's decision — how wikilinks are modelled and resolved — is unchanged and its status stays `accepted`; only that sentence is stale, and this record is where a reader learns so.
- Earlier ADRs refer to the "fixture corpus" in prose. Same thing, now in `examples/`. Their bodies are immutable and a path rename is not a reason to break that.

## The process lesson

Issue #1 was chosen to be implemented first because it was small and **independent of everything else**. It was independent precisely *because it depended on no module code* — and that should have been read as a warning rather than a convenience. "Needs nothing from the module" and "does not test the module" are the same observation.

A checklist-driven review found both symptoms — the test out of step with the spec, the corpus unable to exercise the tests — and diagnosed neither. The cause was a category error in the vocabulary, and it took someone asking what the word "fixture" was doing.

## Alternatives rejected

**Extend the example corpus to cover the wikilink cases.** Would have meant adding embeds, ambiguous basenames, unresolved links and code-span examples to a corpus whose job is to read as a credible knowledge base, while it is frozen and its file count is asserted in three places. It makes the demo worse to serve the tests.

**Keep the test and reimplement the ten extraction rules inside it.** A second mutable home for the rules, which is the failure this repository's layout is built to avoid.

**Keep the test but have it import the real extractor.** Better than the above, and it was the plan until the category error became clear. Rejected because it still asserts a property of example data in the module suite; the extractor's own tests cover the extractor, and they do not need a realistic corpus to do it.
