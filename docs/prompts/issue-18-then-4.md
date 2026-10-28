# Prompt: #18, then #4 if nothing needs a human

A one-off chained run, so two dependent issues can proceed unattended. `/implement-issue` already chains within a label, but this run is two specific issues in order with a human-judgment gate between them, which no skill expresses.

Paste the section below into a session started in this repository.

---

Work two issues in order: **#18 first, then #4.** #4 is blocked by #18, so do not start it until #18 is closed and its closing keyword has fired.

## Sequence

1. **`/implement-issue 18`** — the comparison script's divergence classifier.
2. **Run the comparison script end to end** once #18 is committed, against the private corpus and the committed ground-truth export:
   ```
   uv run python scripts/compare-ground-truth.py \
       --corpus ~/Assistant/obsidian_vaults/brain \
       --ground-truth ~/Assistant/rag-eval/private/obsidian-resolved-links.json
   ```
   Expect **5 intentional, 0 unexplained, exit 0**. Those paths are outside this repo by design (ADR 0008) and are the only thing in this run that the repo cannot tell you.
3. **`/review-brief 4`** — #4 was written before several spec amendments and two decision comments, so review it before building against it.
4. **`/implement-issue 4`** — only if step 3 raised nothing needing a human. See the gate below.

## The gate between #18 and #4

Proceed to step 4 on your own judgment when the review finds only mechanical problems — a stale figure, a wrong cross-reference, a dependency line to correct. Fix those as part of the work and keep going.

**Stop and report instead when any of these is true:**

- The review finds the spec **ambiguous** rather than wrong. A wrong spec you amend in the same commit; an ambiguous one needs a decision that is not yours.
- #18's closing criteria cannot all be met, in particular the script exiting 0 against the committed ground truth.
- The comparison script's output changes in a way #18's issue body does not predict — a sixth disagreement, a class that will not classify, an unexplained pair.
- #4's work turns out to belong partly to another issue, or to require a module the decisions below do not name.
- `Fixes #N` fails to close either issue. That is the mechanism all the tracking rests on and a silent failure matters more than the issue.

Stopping after #18 with a clear reason is a good outcome. Two issues closed on a guess is not.

## What #4 cannot tell you from its body alone

**Read the two comments dated 2026-10-27 on #4 before implementing it.** They carry decisions the body does not, and they are the contract for this issue's module shape:

- **`markdown.py`**, a new lexical leaf module, owns the line-by-line scan and exposes `scan(text) -> Scan` with `code_ranges` and `headings`. `chunker.py` consumes `scan.headings` and **never tracks fence state itself**. `wikilinks._skip_ranges` is moved there, not duplicated.
- **`chunk()` takes body text as an argument**, not a path. No file reading, no import of `corpus.py`. The caller strips frontmatter via `corpus.parse_frontmatter`.
- The second comment corrects the first: **rewiring the comparison script's body links to the chunker's output is #4's job.** What is out of scope is the exit-status question, which is #18.
- A note-centered restructure was considered and **deferred to the end of Phase 1**. Do not design toward it. The shape above is the contract for this phase.

**Both spec amendments named in that comment are part of #4's work**, in the same commit as the code — the spec was deliberately left unedited so the amendment and the implementation cannot disagree.

## Reporting

Per `CLAUDE.md`: findings go in issue comments, which are the record. Chat gets a summary only — which issues were worked, commit SHAs, whether each closing keyword fired, the comparison script's final numbers, and anything that stopped you.

If you stop between the two issues, say plainly what the open question is and what you would need to proceed. Do not pick an answer and note it as a risk.
