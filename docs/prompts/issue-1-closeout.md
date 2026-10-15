# Prompt: close the loop on issue #1

Issue #1 is implemented and closed. Three things remain, and they are the parts of the convention in `CLAUDE.md` that did not happen. That was a prompt bug rather than your mistake: the prompt told you to report to chat, which overrode `CLAUDE.md` saying findings go in issue comments.

## 1. Post your findings as a comment on #1

`gh issue comment 1`. **The comment is the record; chat is not.** Carry over the substance of what you reported: what you implemented, that `Fixes #1` was verified to close the issue, and the four ambiguities you identified. Keep the ambiguities, including the ones that turned out not to matter — a gap that did not bite this time is still a gap in how the brief was written.

Two corrections to fold in:

- The post-exclusion count is **12**, not 13. There are two notes under `people/`.
- Your reading of "expected file count" as the raw on-disk count was **correct**. A fixture-integrity test guards the corpus as it exists, independent of any exclusion logic, which is also why the issue said standalone.

## 2. Amend the spec for the three settled gaps

One commit. The spec is amended by commit when the build proves it incomplete, which this did. In `docs/specs/phase-1-retrieval.md`:

- **Test inventory, fixture corpus integrity:** state that the file count is the **raw on-disk count including excluded paths**, because this test is standalone and does not go through the loader. Name the current number and that post-exclusion is a different figure.
- **Test inventory, fixture corpus integrity:** point at the wikilink-extraction regex rather than leaving a reader to find it in the chunking rules. It is the one authoritative definition of a wikilink target and should be referenced where it is used.
- **A new prerequisite note near the package layout:** a `README.md` must exist at the repo root for `uv sync` to work at all, because `pyproject.toml` names it in the `readme` field and hatchling refuses to build without it. This is a build prerequisite, not a documentation nicety.

Reference the spec sections in the commit message rather than restating them.

## 3. Sort out #16

The README you added is issue **#16**'s subject, and #16 is still open claiming work that now partly exists.

- Comment on #16 pointing at commit `716b009` and saying what the stub already covers.
- Then **rescope #16's body** to only what the stub lacks, against acceptance criterion 11: how to run it against the fixture corpus, that reported numbers come from a private corpus and are not reproducible, and links to `docs/specs/`, `docs/adr/` and `fixtures/README.md`. Leave it open.
- Add a line to #16 noting it is a **prerequisite for every code issue**, not an independent one. My dependency graph had this backwards.

## Do not decide this one

Your third ambiguity — whether a self-link or a wikilink target should match case-insensitively, or tolerate a path segment — **is not yours to settle and should not be guessed.** It affects `chunker.py` (#4) and the graph-expansion experiment in Phase 3, where link resolution rules change what the experiment measures.

Raise it as a comment on **#4** stating the question and why it matters there, and leave it open. Do not change #1's behaviour for it; nothing in the fixture exercises the case today.

## Report back

In chat, only: the comment URLs, the spec-amendment commit SHA, and anything above you disagreed with. The records live on the issues.
