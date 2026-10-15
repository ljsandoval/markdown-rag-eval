# Prompt: implement issue #1

Work GitHub issue #1 in this repository, and nothing else.

Start by reading it:

```
gh issue view 1
```

Then read the spec section that issue names. Conventions, the decisions already made, and the environment are in `CLAUDE.md` — read that too.

## First-run note

The project has never been installed: there is no `uv.lock` and no `.venv`. Run `uv sync` first. The lockfile landing in this commit is expected and fine.

## Report back

1. **What you implemented**, briefly.

2. **Whether `Fixes #1` actually closed the issue on push.** Verify with `gh issue view 1` rather than assuming. This is the main thing being tested here and it has never been confirmed in this repo, so I need the real answer and not the expected one. If it did not close, say so and leave it open — do not close it by hand.

3. **Anything in the issue or the spec that was ambiguous, insufficient, or that you had to guess at.** The brief is meant to be complete on its own. If it wasn't, that is the most useful thing you can tell me, and it is a finding about how these issues are written rather than a failure on your part.

Stop after #1. Do not continue to other issues.
