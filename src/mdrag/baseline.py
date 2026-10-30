"""BM25 keyword baseline over chunks.

Contract: docs/specs/phase-1-retrieval.md -> "Baseline". Tokenization and both
parameters are pinned there; nothing here is tunable.
"""

from __future__ import annotations

import math
import re
from collections import Counter

from mdrag.chunker import Chunk

_TOKEN_SPLIT = re.compile(r"[^a-z0-9]+")

K1 = 1.5
B = 0.75


def tokenize(text: str) -> list[str]:
    """Lowercase, split on ``[^a-z0-9]+``, drop empty tokens. No stemming, no stop words."""
    return [token for token in _TOKEN_SPLIT.split(text.lower()) if token]


class BM25Baseline:
    """BM25 over a fixed set of chunks.

    The spec's ``retrieve`` is a free function, ``retrieve(question, k) -> list[Chunk]``,
    but that signature carries no index or chunk list - it is only implementable as a
    method on an object constructed with the chunks. This class binds the chunks (and
    the BM25 statistics derived from them) at construction, and its ``retrieve`` method
    mirrors the free function's signature exactly: same two positional arguments, same
    return type, same deterministic tie-breaking.
    """

    def __init__(self, chunks: list[Chunk]) -> None:
        self._chunks = chunks
        doc_tokens = [tokenize(c.text) for c in chunks]
        self._doc_len = [len(toks) for toks in doc_tokens]
        self._avgdl = sum(self._doc_len) / len(self._doc_len) if self._doc_len else 0.0
        self._term_freqs: list[Counter[str]] = [Counter(toks) for toks in doc_tokens]
        self._doc_freq: Counter[str] = Counter()
        for tf in self._term_freqs:
            self._doc_freq.update(tf.keys())
        self._n = len(chunks)

    def _idf(self, term: str) -> float:
        n_t = self._doc_freq.get(term, 0)
        return math.log(1 + (self._n - n_t + 0.5) / (n_t + 0.5))

    def _score(self, query_tokens: list[str], doc_index: int) -> float:
        tf = self._term_freqs[doc_index]
        dl = self._doc_len[doc_index]
        norm_len = dl / self._avgdl if self._avgdl else 0.0
        score = 0.0
        for term in query_tokens:
            f = tf.get(term, 0)
            if f == 0:
                continue
            idf = self._idf(term)
            denom = f + K1 * (1 - B + B * norm_len)
            score += idf * (f * (K1 + 1)) / denom
        return score

    def retrieve(self, question: str, k: int) -> list[Chunk]:
        """Score every chunk against the question, return the top k.

        Deterministic tie-breaking: score descending, then note_path ascending,
        then char_start ascending - the same rule `retrieve.py` uses, per the spec.
        """
        query_tokens = tokenize(question)
        scored = [(self._score(query_tokens, i), chunk) for i, chunk in enumerate(self._chunks)]
        scored.sort(key=lambda pair: (-pair[0], pair[1].note_path, pair[1].char_start))
        return [chunk for _, chunk in scored[:k]]
