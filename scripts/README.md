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

**It currently exits 1 on the target corpus, by design.** As of 2026-10-16 it
reports 25 pairs found only by `mdrag`, 2 found only by Obsidian, and 14 pairs
agreeing on existence while differing by one on count. All 41 trace to the
three rules the spec gained the same day, and the code implementing those rules
is the open issue. This is the failing baseline: the numbers should go to zero
when that issue closes, and a test that has never failed proves nothing.
