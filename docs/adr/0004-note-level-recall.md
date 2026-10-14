---
status: accepted
date: 2026-10-14
---

# 0004. Note-level recall is the headline metric

## Context

Recall@k asks whether the right material appeared in the top k results. For a corpus chunked by heading, "top k" is ambiguous, and the ambiguity changes the number substantially.

A single long note yields several chunks. A query matching that note strongly can fill all five of the top five slots with chunks of it.

## Decision

Report three granularities and headline the second.

| Metric | Hit when |
|---|---|
| `chunk_recall@k` | Any of the top k **chunks** belongs to an expected note |
| **`note_recall@k`** | The expected note is among the top k **distinct notes**, after deduplicating the full ranked list |
| `exact_chunk_recall@k` | A top k chunk has both the expected note and the expected heading |

Report the curve at k = 1, 3, 5, 10 for all three, plus the rank of the first correct hit and mean reciprocal rank.

## Why note-level

Chunk-level recall overstates what was tested. If four of the top five chunks come from one note, the retriever was given five attempts at two candidates, and calling that recall@5 misrepresents the difficulty.

Note-level recall is also closer to what the generation step receives. Four chunks of one note is one note's worth of material in the context window. Since the question the whole system answers is "did the answer material reach the prompt", the metric that approximates that is the one to headline.

Reporting all three costs two extra lines once the list is sorted, and the gap between chunk-level and note-level is itself informative.

## Consequences

- The published number is the conservative one. Chunk-level would look better and mean less.
- Which granularity is being reported must be stated wherever a number is quoted. Most write-ups in this area do not say, which is part of why figures across projects are not comparable.
- Multi-hop questions, where the answer spans two notes, require every expected note to be retrieved rather than any one of them. Expect this to be the worst figure in the report; it is the case the planned retrieval experiment exists to improve.

## Alternatives rejected

**Chunk-level as the headline** - the obvious implementation, and it inflates with note length.

**nDCG** - requires graded relevance judgements rather than binary ground truth, and is hard to read at 25 questions.

**Precision@k** - mechanically tiny when one or two notes out of thousands are correct, and uninformative here.
