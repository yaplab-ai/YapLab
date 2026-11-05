"""Local lexical TF-IDF search over the prepared, scoped notebook chunks.

This is an in-memory inspection aid, not an embedding or FAISS index. Results
are curated summaries, not full texts or legal determinations.
"""
from __future__ import annotations

from collections import Counter
import json
import math
from pathlib import Path
import re

from .evidence import tokens
from .export import export_bundle

_WORD = re.compile(r'[a-z0-9]+')


def _counts(text: str) -> Counter[str]:
    allowed = tokens(text)
    return Counter(word for word in _WORD.findall(text.lower()) if word in allowed)


class ChunkIndex:
    """Build a sparse index after validating the whole bundle against the corpus."""

    def __init__(self, bundle: Path, institution: str = 'general') -> None:
        bundle = Path(bundle)
        export_bundle(bundle, check=True, institution=institution)
        self.manifest = json.loads((bundle / 'manifest.json').read_text(encoding='utf-8'))
        self.chunks = [json.loads(line) for line in
                       (bundle / 'chunks.jsonl').read_text(encoding='utf-8').splitlines()]
        counts = [_counts(chunk['text']) for chunk in self.chunks]
        document_frequency: Counter[str] = Counter()
        for words in counts:
            document_frequency.update(words.keys())
        n = len(counts)
        self.idf = {term: 1 + math.log((n + 1) / (frequency + 1))
                    for term, frequency in document_frequency.items()}
        self.vectors = [self._vector(words) for words in counts]

    def _vector(self, counts: Counter[str]) -> dict[str, float]:
        weighted = {term: count * self.idf[term] for term, count in counts.items()
                    if term in self.idf}
        norm = math.sqrt(sum(value * value for value in weighted.values()))
        return {term: value / norm for term, value in weighted.items()} if norm else {}

    def search(self, query: str, limit: int = 5) -> list[dict]:
        """Return positive cosine matches, deterministically ordered, or abstain."""
        if not 1 <= limit <= 100:
            raise ValueError('limit must be between 1 and 100')
        query_vector = self._vector(_counts(query))
        if not query_vector:
            return []
        results = []
        for chunk, vector in zip(self.chunks, self.vectors):
            matched = sorted(query_vector.keys() & vector.keys())
            if not matched:
                continue
            score = sum(query_vector[term] * vector[term] for term in matched)
            source = self.manifest['sources'][chunk['source']]
            results.append({
                'source_id': source['id'], 'source_url': source['url'],
                'source_scope': source['scope'], 'source_institution': source['institution'],
                'source_verification': source['verification'],
                'source_document_type': source['document_type'],
                'source_jurisdiction': source['jurisdiction'],
                'source_published': source['published'], 'source_retrieved': source['retrieved'],
                'source_file': chunk['source'], 'chunk_id': chunk['chunk_id'],
                'text': chunk['text'], 'matched_terms': matched, 'score': score,
            })
        results.sort(key=lambda result: (-result['score'], result['source_id'], result['chunk_id']))
        return results[:limit]
