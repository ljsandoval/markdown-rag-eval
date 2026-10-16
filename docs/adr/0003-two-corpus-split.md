---
status: accepted
date: 2026-10-14
supplemented-by: "0008"
---

# 0003. Two corpora, and the measurement artifacts stay private

## Context

This repository is public. The corpus the numbers are measured against is private.

The index is a build artifact and was never the exposure. The **measurement artifacts** are: an eval set records which note holds each answer, so a file path alone discloses the existence and subject of a private note; a per-question results file contains verbatim retrieved text; and a failure analysis quotes passages to explain misses.

So the artifacts that make this project falsifiable are precisely the ones that cannot be published.

## Decision

Two corpora with different jobs, and the split runs through to the repository layout.

| | Fixture corpus | Private corpus |
|---|---|---|
| Size | 14 synthetic notes | ~698 notes |
| Job | Prove the code runs; let anyone reproduce the demo | Produce the numbers that get reported |
| Eval set | 8 to 10 questions, public | 25 questions, 10 held out, private |
| Results | Public | Private |

The reported numbers come from the private corpus and are **labelled unreproducible, with the reason given**. The fixture corpus deliberately does not produce the headline figures.

The corpus is a command-line argument. The tool makes no assumption about where it came from and contains no knowledge of the application that produced the private one.

## Why the fixture does not produce the headline

A recall figure measured over notes and questions written by the same person is close to circular. It demonstrates that the pipeline executes, not that retrieval works on real text. Paying for a reproducible-but-circular number would also cost a second labelled eval set and an experiment that cannot replicate, because a synthetic corpus's link topology is whatever its author generated.

## Consequences

- Anyone can clone this repository and reproduce the fixture-corpus numbers exactly. Nobody can reproduce the reported ones, and the README says so rather than implying otherwise.
- Exclusions are enforced by test, not by convention: journal content, client material, and notes about named third parties are excluded at discovery, so an excluded file is never read and cannot reach a results file.
- The fixture corpus is frozen once a published number depends on it.
- Reporting two measurements is more honest than one and reads better, because it shows reproducibility and confidentiality were separated deliberately.

## Alternatives rejected

**One public corpus only** - would make every number reproducible and every number circular.

**One private corpus only** - would make the repository a tool nobody can run, which defeats the point of publishing it.

**A large synthetic corpus built to carry the headline numbers** - rejected above, and it would have forced a re-labelled eval set plus an unreplicable experiment.

