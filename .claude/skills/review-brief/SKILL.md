---
name: review-brief
description: Review the spec and its issues for gaps before implementation starts. Checks build prerequisites, that issue pointers resolve, dependency order, undefined terms, internal cross-references, and requirements restated instead of referenced. Fixes mechanical defects, escalates anything needing a decision. Takes an issue number, a label such as phase-1, or nothing for everything open.
model: opus
---

# Review the brief

Argument: `$ARGUMENTS` — an issue number, a label, or empty meaning every open issue.

**Before anything else, state which model you are.** One line. This skill pins a model deliberately, the pin is a silent per-invocation override that the status line does not reflect, and the review is the one procedure here where the model choice is the point. Saying it makes the pin verifiable in the moment rather than only afterwards in the session transcript.

Review the brief before anything is built against it: the spec, and the issues that reference it. Find gaps. Change as little as possible.

**You are not implementing anything.** No feature code, no tests for features, no closing issues.

## What to read

`CLAUDE.md` for the conventions. `docs/specs/` for the contract. `docs/adr/` for what was already decided and rejected. Then the issues in scope, with `gh issue view N`.

Scope is the argument given: a single issue number, a label such as `phase-1`, or nothing, meaning every open issue.

## The checklist

Each item exists because it cost real time once. Work them in order and report per item, including the ones that pass — "checked, nothing found" is a useful result and its absence is ambiguous.

**1. Can a clean checkout install and run the test suite?**

Not "does it work here" — does it work from nothing. Build-system prerequisites are the class that hides: a `pyproject.toml` naming a file that must exist before the backend will build, a tool assumed present, a lockfile nobody generated. This is the check that would have caught a README blocking `uv sync` on the first run, which was filed as an independent issue while actually blocking every other one.

**2. Does every issue's "Closes when" point at a spec section that contains the thing?**

Issues reference the spec and never restate it, which only works if the reference lands. Check each pointer resolves to a section, and that the section actually carries what the issue needs. One issue once pointed at "Test inventory" for a regex that lived in the chunking rules.

**3. Is the stated dependency order correct, including toolchain order?**

Read the graph, not the prose: `gh issue list --state open --json number,title,blockedBy --limit 50` returns every edge in one call, with each blocker's state. Ask whether each edge is true, and whether anything missing should be there. Logical dependencies between modules are the easy half; the half that gets missed comes from the build and the tooling.

Some bodies still carry a `**Blocked by:**` line predating the dependency graph. **The graph is authoritative.** Where a line disagrees with it, that is a finding worth reporting, not a line to quietly match — one of the two is wrong and which one tells you something.

**4. Does the spec define every term its acceptance criteria use?**

Walk the criteria and the test inventory looking for terms that are never defined. "Expected file count" and "no self-links" were both undefined on the first run — one got guessed correctly, and the other turned out to govern a later phase's experiment.

**5. Do internal cross-references in `docs/` resolve to headings that exist?**

A spec is amended by commit, amendments are commits, and commits conflict. Two amendments hours apart once left a reference pointing through a relocated rule. Prefer section names over positions when proposing fixes, since titles survive renumbering.

**6. Does any issue restate a spec requirement rather than referencing it?**

A restated requirement is a second mutable home for the same fact and will drift. Flag any that has already drifted from the spec text it duplicates.

## What to do with what you find

Two kinds, and the distinction is the whole point of a review being separate from implementation.

**Mechanical defects — fix them.** A dangling cross-reference, a dependency that is plainly missing or plainly wrong, a typo in a path. One commit, referencing the sections touched. These have one correct answer and no judgement in them. A missing or wrong edge is fixed with `gh issue edit N --add-blocked-by M` / `--remove-blocked-by M`, which is bidirectional, so never edit the other issue to match.

**Anything needing a decision — do not decide it.** An undefined term, an ambiguous requirement, a missing acceptance criterion, a dependency that might be deliberate. Post a comment on the issue it affects, state the question and why it matters, and **leave it open**. A review that quietly resolves ambiguities removes the reason it was run.

If a gap affects a later phase rather than the issue in front of you, say so on the issue where it will bite, not the one where you found it.

## Report

In chat, a per-item summary of the checklist with pass or finding, the commit SHA if you fixed anything mechanical, and the comment URLs for anything escalated. Name explicitly which findings need a human decision before implementation should start.
