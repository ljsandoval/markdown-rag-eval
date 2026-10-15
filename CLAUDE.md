# CLAUDE.md — markdown-rag-eval

Retrieval over a markdown corpus, with an eval harness that measures it.

## How work arrives here

One GitHub issue per unit of work. **Your brief is the issue plus the spec section it names.** Run `gh issue view N`, then read that section.

| Where | What it is |
|---|---|
| `docs/specs/` | The **contract**: what is true of the finished thing. Authoritative. |
| `docs/adr/` | Decisions, and what was rejected. Bodies immutable; only `status:` changes. |
| `fixtures/README.md` | The corpus the tests assert against, and why each note is in it. |

Issues reference spec sections and never restate them. **If an issue and the spec disagree, the spec wins** — and say so in a comment on the issue.

## Invocable procedures

Two skills in `.claude/skills/`, each pinned to its own model. They hold **procedure**; this file holds **conventions**; neither restates the other.

| Skill | Model | Takes | Does |
|---|---|---|---|
| `review-brief` | opus | issue number, label, or nothing | Checks the spec and issues for gaps before implementation. Fixes mechanical defects, escalates anything needing a decision. |
| `implement-issue` | sonnet | issue number or label | Works one issue, or every unblocked issue with that label. |

Run `review-brief` before implementing against a contract that has not been reviewed since it changed.

## Rules

**The spec is amended by commit.** If implementing something proves a statement in the spec wrong, change the spec in the *same commit* as the code that proved it, and say why in an issue comment. Never work around a wrong spec silently — a spec that disagrees with the code is the failure this layout exists to prevent.

**Findings go in issue comments.** `gh issue comment N`. Measurements, things you checked, things that surprised you, numbers you got. Never a new markdown file: there is no reviews directory and no notes directory, deliberately.

**Commits close issues.** Put `Fixes #N` in the commit message and push to `main`. Do not close an issue by hand — the commit is what sets the state, and if the keyword stops firing that is something to report.

**`fixtures/corpus/` is frozen.** Tests assert against it and published numbers are measured on it, so editing a note silently invalidates both. A test failing because the corpus looks wrong is a finding to report, not a file to fix.

**Do the issue you were given.** Other open issues are not yours unless you were named to them.

**Never commit an index or a private measurement artifact.** Both are gitignored build outputs. The eval set and results files for the private corpus do not belong in this repository at all — see ADR 0003.

## Decisions already made

Do not relitigate these in code. Each has an ADR with the alternatives that were rejected.

| Decision | ADR |
|---|---|
| No vector database; an exhaustive NumPy scan is faster at this corpus size | 0001 |
| Embeddings run locally; no hosted embedding API, for any corpus | 0002 |
| Two corpora, and measurement artifacts stay private | 0003 |
| Note-level recall is the headline metric | 0004 |

**When is a new ADR warranted?** All three must hold: there was a real alternative a competent person would have chosen, the decision outlives the code implementing it, and a future reader would otherwise relitigate or quietly undo it. Most work needs none. A thing the spec already states is not an ADR; neither is a reversible choice with a measurable answer, which belongs in a results file. ADR 0000 carries the rest.

## Environment

- Python 3.11, managed with `uv`. pytest, ruff, mypy, all configured in `pyproject.toml`. `disallow_untyped_defs = true`.
- `gh` authenticates from the macOS keyring and does not prompt. If a `gh` call ever hangs for a minute, a 1Password shell plugin has been reinstated for it — that is the cause, every time.
- `git push` uses SSH through the 1Password agent and raises one Touch ID prompt. Expected, not a failure.
