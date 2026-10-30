---
name: implement-issue
description: Implement one GitHub issue, or every unblocked issue carrying a label. Reads the issue and the spec section it names, implements, posts findings as an issue comment, closes via a Fixes commit, and verifies the close actually fired. Resolves blockers from GitHub issue dependencies, not from body prose. Stops rather than guessing when the spec is ambiguous. Takes an issue number or a label such as phase-1.
model: sonnet
---

# Implement

Argument: `$ARGUMENTS` — an issue number, or a label.

Implement issues. Conventions are in `CLAUDE.md` and are not repeated here — this file is the procedure, that file is the contract, and neither restates the other.

Scope is the argument given: a single issue number, or a label such as `phase-1` meaning every unblocked issue carrying it.

## Selecting what to work

**Blockers come from GitHub issue dependencies.** One call returns the graph, and each blocker node carries its state:

```sh
gh issue list --state open --label <label> --json number,title,blockedBy --limit 50
```

An issue is **unblocked when every node in its `blockedBy` is closed, or it has none**.

**Never read a `Blocked by:` line from a body to decide this.** Some issues still carry one from before the convention changed; it is prose kept for the reasoning it holds, it is not authoritative, and it can disagree with the graph. The graph wins. If you notice a disagreement, say so in a comment on the issue rather than fixing it silently — one of them is wrong and which one matters.

For a single issue number: `gh issue view N --json state,blockedBy`, confirm it is open and unblocked, then work it.

For a label: work the unblocked ones. **If nothing is unblocked, stop and say so.** That is a finding about the dependency graph, not a reason to pick something anyway.

Do not reorder around a blocker. Do not start something whose blocker is merely "nearly done".

**If the work reveals a dependency that is not recorded, record it** — `gh issue edit N --add-blocked-by M` — and say so in your report. The edge is bidirectional automatically, so never edit both issues.

## Working one issue

Per issue, in this order:

1. `gh issue view N`. Read the spec section it names. The spec is the contract; the issue is a pointer to it.
2. Implement. Tests land with the code, not after.
3. `ruff` and `mypy` clean before committing.
4. **Post findings as a comment on the issue** — `gh issue comment N`. Measurements, anything that surprised you, anything you had to decide. This is the record; chat is not.
5. Commit with `Fixes #N` and push.
6. **Verify the issue actually closed**, with `gh issue view N`. Do not close it by hand.
7. Re-evaluate what is now unblocked, and continue.

## Stop conditions

Stop and report rather than working around any of these:

- Tests fail in a way the spec does not explain.
- The spec is **ambiguous** rather than wrong. A wrong spec you amend in the same commit, per `CLAUDE.md`; an ambiguous one needs a decision that is not yours.
- `Fixes #N` did not close the issue. That is the mechanism the tracking rests on and a silent failure matters more than the issue. Note that issue dependencies are advisory and never prevent a close, so a blocked issue is not an explanation for this.
- A change would touch a frozen fixture.
- An issue's work turns out to belong to a different issue.

Stopping with one issue done and a clear reason beats four issues done on guesses.

## Do not

- Work an issue outside the given scope, however small or tempting.
- Decide something the spec leaves open — comment on the issue and leave it.
- Restate spec requirements in code comments or commit messages. Point at the section.
- Close an issue by hand.

## Report

In chat, only: which issues were worked and their outcomes, the commit SHAs, whether each closing keyword fired, and anything that stopped you. The detail lives in the issue comments.
