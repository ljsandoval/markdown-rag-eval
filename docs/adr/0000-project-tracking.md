---
status: accepted
date: 2026-10-14
---

# 0000. How this repository is tracked

## Context

A previous project in this workspace produced six planning documents and three review documents for one module. Nearly every one opened with a header stating that parts of it were superseded and naming a different document to read instead. The diagnosis was not bad naming: the same facts lived in two mutable places with nothing between them, and the step that was supposed to reconcile them ran once in three attempts.

## Decision

Six document types, each answering one question, each with one home.

| Type | Answers | Lives | Mutability |
|---|---|---|---|
| Design note | Why this direction? What was rejected? | Private notes | Frozen once decided |
| ADR | What was decided, and what did it cost? | `docs/adr/` | Body immutable; `status:` is the only mutable field |
| Spec | What is true of the finished thing? | `docs/specs/` | Amended by commit |
| Issue | What remains to be done? | GitHub Issues | Binary, closed by a commit |
| Finding | What did I observe checking this against reality? | Issue comments | Append-only |
| Outcome | What shipped? What is still open? | Private project note | Append |

Four conventions, each with a mechanism rather than a reminder behind it:

- **ADRs are numbered and never renumbered.** The body is immutable after acceptance; a later decision supersedes an earlier one by adding a record and flipping `status:`, never by editing the original.
- **An issue is sized so one merge closes it.** This is self-correcting: get it wrong and the closing keyword stops firing, which is visible immediately.
- **Issues reference a spec section and never restate it.** A restated requirement is a second mutable home, and a drifted one is visible in the diff.
- **The spec is amended by commit, in the same pull request as the code that proved it wrong.**

## Why the spec lives here and not in the design notes

Because it deletes the only step in the loop that empirically does not happen.

When a build proves a spec wrong, a spec that lives outside the repository cannot be fixed by the session doing the building without crossing a boundary that exists to keep that session focused on the code. So the fix gets deferred to a later session, and deferred fixes are the step that ran once in three. A spec inside the repository is amended by the same commit that proved it wrong, and nothing is deferred.

## Consequences

- The spec stops being part of the private notes graph: no backlinks, no link resolution into the surrounding notes. That is a real loss and it is smaller than it first appears, since the repository can be opened as a second vault for reading.
- An issue that merely references the spec is terse by design. Read the named section; it is the contract.
- There is no fold-back step and no synchronising command. A finding is an issue comment, already attached to the work and already ordered.
- The remaining residual risk: the private project note is a derived summary and can go stale. When it does, the repository is still correct, which is a weaker failure than two documents contradicting each other.

## Alternatives rejected

**Markdown conventions in the notes, with a command to synchronise them.** This was the opposing proposal and it loses on its own evidence: every rule it proposed needed a remembered action, and the one it most needed had already failed twice.

**A self-hosted tracker.** Rejected on the host's own limits: no issue hierarchy, no projects API, no export, and reachable only over a private network. The deciding reason is simpler - the commit and the issue should be the same object in the same system, which is the only arrangement where the state transition is free.

