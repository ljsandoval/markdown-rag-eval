---
status: accepted
date: 2026-10-14
---

# 0002. Embeddings are computed locally

## Context

The private corpus this tool is measured against is a personal knowledge base of roughly 600,000 words. It includes journal entries, notes about named third parties, and material covered by a client confidentiality obligation that survives termination of the engagement.

Embedding requires sending every chunk of text to a model.

## Decision

Use a `sentence-transformers` model running locally on CPU. No hosted embedding API, for any corpus.

## Why

A hosted embedding API would mean transmitting the entire private corpus to a third party. For the journal and the client material that is not a preference, it is disqualifying.

Two further reasons that would not be sufficient alone but point the same way. There is no first-party embeddings endpoint from the model vendor used elsewhere in this project, so a hosted embedding step means a second vendor and a second credential. And local inference costs nothing per run, which matters for a tool whose eval is designed to be re-run often.

## Consequences

- Model weights are cached locally on first run; every later run is offline, and the index build does not require the network.
- The model and its pinned revision are recorded in the index metadata and in every results file. A model identifier alone is not reproducible, because a model repository can be updated in place.
- Chunking inherits a hard constraint: a small model's maximum sequence length is commonly 256 or 512 tokens and text beyond it is **silently truncated**, producing an ordinary-looking vector for a fragment. The chunk ceiling therefore derives from the model rather than from preference, and the index build reports how many chunks exceed it.
- The operational experience of a managed enterprise vector and embedding service is not covered by this project. The architecture is the same and the swap is one interface, but the claim stops there and should be stated that way.

## Alternatives rejected

**A hosted embedding API** - disqualified by the corpus contents, not by cost.

**Embedding a redacted subset of the corpus** - considered and rejected: it would produce a measurement on a corpus nobody actually has, and the exclusion mechanism already handles the material that must not be indexed at all.

