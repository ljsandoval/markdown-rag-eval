---
status: accepted
date: 2026-10-15
---

# 0006. `sentence-transformers` is a required dependency

## Context

ADR 0002 decided embeddings run locally on CPU. That requires `sentence-transformers`, which pulls `transformers`, which pulls `torch`. Neither was declared in `pyproject.toml`, so whoever implemented first would have added it as an undiscussed side effect.

`torch` is the execution engine for the model: an embedding model is a transformer encoder, and producing a vector means pushing text through its layers as matrix multiplications. It is not an optional convenience in that chain.

The concern was install weight against two promises the spec makes — acceptance criterion 4, that a clean checkout runs both commands against the fixture corpus, and criterion 11, that the README shows a reader how to reproduce something.

## What was measured, 2026-10-15

Against a throwaway project, not estimated.

| | macOS arm64 | Linux x86_64 |
|---|---|---|
| `torch` wheel | 127 MB | 555 MB |
| CUDA packages pulled | **none** | **15**, from PyPI, marked `sys_platform == 'linux'` |
| Full environment installed | **797 MB** | not measured; the CUDA packages are where multi-gigabyte figures come from |
| `uv sync` wall time | 12 s | — |

Of the 797 MB on macOS, `torch` is 527 MB installed from a 127 MB wheel. The platform markers do the right thing unprompted: **zero CUDA packages install on macOS**, so the weight concern is entirely a Linux concern.

## Decision

Declare `sentence-transformers` and `numpy` in `[project.dependencies]`. No optional extra, no index pinning.

## Why not an optional extra

An extra would keep a clone cheap, and the case for it is real: BM25 needs none of this, and the baseline is a first-class deliverable rather than a degraded mode (ADR 0004).

It loses on three counts.

**It breaks acceptance criterion 4.** With the extra, `uv run mdrag index` does not work from a clean checkout. The criterion would have to be amended to say "with the extra installed", which weakens a promise to protect against a cost no current user pays.

**It makes the test suite able to pass without testing anything.** The natural implementation is `importorskip`, and then a clean run is green with every embedding test silently skipped. Avoidable, but it needs a marker, a CI job with the extra, and something that fails when the full suite never ran — machinery in service of a problem that is hypothetical here.

**The cost it avoids is not being paid.** The developer is on macOS, where the install is 797 MB and takes twelve seconds, against an existing environment of 108 MB. A Linux visitor paying for CUDA is a real cost and a hypothetical person.

## Why not pin the CPU-only torch index

**Attempted and it did not work.** This configuration was tried:

```toml
[[tool.uv.index]]
name = "pytorch-cpu"
url = "https://download.pytorch.org/whl/cpu"
explicit = true

[tool.uv.sources]
torch = [{ index = "pytorch-cpu", marker = "sys_platform == 'linux'" }]
```

uv 0.12.17 **accepted it without error and ignored it.** The resulting lockfile records one `torch` entry sourced from `pypi.org/simple`, with all fifteen CUDA packages intact and marked for Linux. A configuration that is accepted and silently ineffective is worse than one that fails, because it reads as solved.

The mechanism may well be achievable with a different form; what is recorded here is that the obvious form does not work and was not pursued further, because the cost it would avoid is not currently being paid.

## Consequences

- A clean checkout runs everything. Criteria 4 and 11 hold unamended, which was the point.
- No guarded imports, no skippable tests, no per-invocation `--extra` flag.
- **A Linux clone pulls roughly 15 CUDA packages this project will never use**, since ADR 0002 committed to CPU. That is a known, documented waste rather than an oversight.
- `numpy` is declared here rather than left implicit, which ADR 0001's exhaustive scan depends on.

## When to revisit

Any of: someone actually reports the Linux install cost; CI starts running on Linux and the install time matters; or a working form of the CPU index pin is verified, at which point it is a strict improvement with no promise weakened.

The extra becomes right only if a cheap clone starts mattering more than criterion 4, which would be a change in what this repository is for.
