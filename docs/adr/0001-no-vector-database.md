---
status: accepted
date: 2026-10-14
---

# 0001. No vector database

## Context

The corpus is roughly 6,000 chunks. A small sentence-transformer model produces 384-dimensional vectors, so the entire index is a 6,000 x 384 array of 32-bit floats: about 9 MB.

Every recognisable RAG architecture puts a vector database here, and the role's vocabulary expects one.

## Decision

Store the index as a NumPy array on disk with a JSON sidecar for chunk metadata. Score a query by one matrix-vector product against every chunk.

## Why

An approximate-nearest-neighbour index exists to avoid comparing a query against every vector. At this scale, comparing against every vector is 2.3 million multiply-accumulates, which NumPy completes in well under a millisecond - faster than the bookkeeping an index would add, and exact rather than approximate.

Adding a vector database would mean a dependency, a service or file format to version, a build step, and a second place the embedding dimension is asserted, in exchange for making a sub-millisecond operation slower and less accurate.

## Consequences

- The index is a build artifact, rebuilt from the corpus in minutes, and is not committed.
- Retrieval has no recall/latency tradeoff to tune, because the search is exhaustive.
- Being able to show the arithmetic is a better answer to "why no vector database" than having reached for one by default.

## When to revisit

Either of: the corpus grows by roughly an order of magnitude, or sub-millisecond query latency starts to matter. Neither is true, and neither is close.

## Alternatives rejected

**FAISS** - the library named in the role description this project is partly aimed at. Rejected for this corpus size; it would be the right answer an order of magnitude up.

**sqlite-vec** - simpler to operate than FAISS and queryable with SQL. Rejected for the same reason, and it remains the first thing to reach for if the revisit condition is met.

**A hosted vector service** - rejected on two counts beyond scale: it costs money against a zero-cost constraint, and it requires sending a private corpus to a third party. See ADR 0002.

