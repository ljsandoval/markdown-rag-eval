# scripts/

Verification tools. Not part of the package, not run by the test suite, and
corpus-agnostic like everything else here: they take paths.

| Script | What it does |
|---|---|
| `obsidian-export-resolved-links.js` | Exports Obsidian's own link resolution as ground truth. Pasted into Obsidian's developer console; the procedure is in its header. |
| `compare-ground-truth.py` | Compares `mdrag`'s resolution against that export and classifies every disagreement. |

## Why these are not tests

They need a real corpus and a hand-made export, so they cannot run in CI and
they cannot assert a fixed number - a corpus grows. The module suite asserts
module behaviour against purpose-built inputs (ADR 0007); these answer a
different question: does the implementation agree with the reference resolver
on a corpus nobody designed to make it pass.

## Running the comparison

```
uv run python scripts/compare-ground-truth.py \
    --corpus /path/to/corpus \
    --ground-truth /path/to/obsidian-resolved-links.json
```

Exit status is 1 while any disagreement is unexplained, so it can gate a
commit once the known classes are resolved.

**It still exits 1 on the target corpus, and that is expected.** #17 implemented
the three rules behind the 2026-10-16 baseline's 41 disagreements. A fresh
export on 2026-10-27 agreed on 2,269 of 2,272 resolved pairs; the remaining
five all trace to the divergences the spec's Validation section names as
known and intentional (the basename fallback, and same-note heading
references), not to an unstated rule. A corpus with any such link will always
produce a nonzero exit here - "zero disagreements" means zero *unexplained*
ones, per the Validation section's own framing.
