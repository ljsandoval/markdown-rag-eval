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

Exit status is 1 only while a disagreement is **unexplained**. The three
classes the spec's Validation section names as known and intentional -
basename fallback, same-note heading references, and ambiguity - are
classified, counted, and printed under their own headings, but excluded from
the exit status. Anything matching none of them is reported as unexplained
and is the only thing that fails the run.

**It exits 0 on the target corpus.** #17 implemented the three rules behind
the 2026-10-16 baseline's 41 disagreements; #18 added the classifier above so
the known survivors stop masking a real regression. A fresh export on
2026-10-27 agreed on 2,269 of 2,272 resolved pairs, and every one of the
remaining five is classified: 3 same-note heading references, 1 basename
fallback, and 1 further count disagreement also caused by the basename
fallback. Five intentional, zero unexplained, exit 0.
