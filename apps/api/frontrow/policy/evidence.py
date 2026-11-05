"""Small, inspectable lexical index over the packaged policy source notes.

These notes are starting points for further reading, not legal determinations.
"""
from __future__ import annotations

import json
import math
import re
from functools import lru_cache
from importlib import resources
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

Topic = Literal['privacy', 'accessibility', 'responsible_ai', 'education', 'human_oversight']
Institution = Literal['general', 'uaeu']


class Source(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    authority: str = Field(min_length=1)
    url: str = Field(min_length=1)
    jurisdiction: str = Field(min_length=1)
    document_type: str = Field(min_length=1)
    published: str
    retrieved: str
    scope: str = Field(min_length=1)
    source_locator: str = Field(min_length=1)
    topics: list[str] = Field(min_length=1)
    summary: str = Field(min_length=1)
    requirements: list[str]
    limitations: list[str]
    institution: str | None = None
    reuse_note: str | None = None
    verification: str | None = None
    text_path: str | None = None
    text_sha256: str | None = None
    text_retrieved: str | None = None
    text_locator: str | None = None
    text_rights: str | None = None
    text_status: str | None = None


class Corpus(BaseModel):
    model_config = ConfigDict(extra='forbid')
    version: str = Field(min_length=1)
    description: str
    limitations: list[str]
    entries: list[Source] = Field(min_length=1)


class CorpusUnavailable(RuntimeError):
    """The evidence cannot be safely served."""


@lru_cache(maxsize=1)
def load_corpus() -> Corpus:
    try:
        data = resources.files('frontrow.policy').joinpath('corpus.json').read_text(encoding='utf-8')
        corpus = Corpus.model_validate(json.loads(data))
        ids = [entry.id for entry in corpus.entries]
        if len(ids) != len(set(ids)):
            raise ValueError('duplicate source IDs')
        return corpus
    except (OSError, ValueError, TypeError, ValidationError) as exc:
        raise CorpusUnavailable('Policy source notes are unavailable or invalid.') from exc


_STOP = frozenset('a about after all an and are as at be been but by can could did do does for from had has have how i if in into is it its may might my of on or our should so than that the their them then there these they this those to us use using was we were what when where which who will with would you your'.split())
_WORD = re.compile(r"[a-z0-9]+")
# Curated retrieval cues, not claims that a source specifically governs the
# activity. Values only broaden lookup toward existing corpus vocabulary.
_ALIASES = {
    'caption': ('accessibility', 'disability'),
    'captions': ('accessibility', 'disability'),
    'screen reader': ('accessibility', 'disability'),
    'retention': ('personal', 'data', 'privacy'),
    'grading': ('assessment', 'education', 'human', 'oversight'),
    'ai': ('artificial', 'intelligence'),
}


def query_expansions(text: str) -> dict[str, list[str]]:
    words = tokens(text)
    return {alias: list(terms) for alias, terms in _ALIASES.items()
            if (bool(re.search(r'\bscreen[\s-]+reader\b', text, re.IGNORECASE))
                if alias == 'screen reader' else alias in words)}


def tokens(text: str) -> set[str]:
    return {word for word in _WORD.findall(text.lower()) if (len(word) >= 3 or word == 'ai') and word not in _STOP}


def _fields(source: Source) -> list[tuple[float, set[str]]]:
    return [
        (3.0, tokens(source.title + ' ' + ' '.join(source.topics).replace('_', ' '))),
        (2.0, tokens(source.scope + ' ' + source.summary)),
        (1.0, tokens(' '.join(source.requirements) + ' ' + source.authority)),
    ]


def scoped_sources(corpus: Corpus, institution: Institution = 'general') -> list[Source]:
    """Filter before ranking or fallback; text never chooses a reference collection."""
    if institution not in ('general', 'uaeu'):
        raise ValueError('Unknown institution scope')
    return [source for source in corpus.entries
            if source.institution is None or (institution == 'uaeu' and source.institution == 'uaeu')]


def lexical_search(corpus: Corpus, query: str, limit: int = 5, topic: Topic | None = None,
           institution: Institution = 'general') -> list[dict]:
    """Rank matching words with field weights and IDF; return no zero-match hits."""
    entries = scoped_sources(corpus, institution)
    original_terms = tokens(query)
    expansions = query_expansions(query)
    query_terms = original_terms | {term for terms in expansions.values() for term in terms}
    if not query_terms:
        return []
    indexed = [(source, _fields(source)) for source in entries]
    frequency = {term: sum(any(term in words for _, words in fields) for _, fields in indexed)
                 for term in query_terms}
    results = []
    for source, fields in indexed:
        if topic and topic not in source.topics:
            continue
        matched = sorted(term for term in query_terms if any(term in words for _, words in fields))
        if not matched:
            continue
        score = sum(max(weight for weight, words in fields if term in words)
                    * (1 if term in original_terms else 0.7)
                    * (1 + math.log((len(indexed) + 1) / (frequency[term] + 1)))
                    for term in matched)
        # Preserve explicitly named standard versions. Tokenisation excludes
        # the individual digits, so otherwise 2.1 and 2.2 look identical.
        if re.search(r'\bwcag\s*2\.1\b', query, re.IGNORECASE) and re.search(
                r'\bwcag\s*2\.1\b', source.scope + ' ' + source.summary, re.IGNORECASE):
            score += 12
        results.append({**source.model_dump(), 'score': round(score, 3), 'matched_terms': matched,
                        'query_expansions': {alias: [term for term in terms if term in matched]
                                             for alias, terms in expansions.items()
                                             if any(term in matched for term in terms)}})
    results.sort(key=lambda result: (-result['score'], result['id']))
    return results[:limit]


def fuse_rankings(lexical: list[dict], vector_ids: list[str], allowed: dict[str, Source], limit: int) -> list[dict]:
    """Fuse source ranks using reciprocal rank fusion after scope/topic filtering."""
    lexical_by_id = {hit['id']: hit for hit in lexical}
    scores: dict[str, float] = {}
    for rank, hit in enumerate(lexical, 1):
        scores[hit['id']] = 1 / (60 + rank)
    seen: set[str] = set()
    for source_id in vector_ids:
        if source_id not in allowed or source_id in seen:
            continue
        seen.add(source_id)
        scores[source_id] = scores.get(source_id, 0) + 1 / (60 + len(seen))
    hits = []
    for source_id in sorted(scores, key=lambda item: (-scores[item], item))[:limit]:
        hit = dict(lexical_by_id.get(source_id) or {**allowed[source_id].model_dump(),
                                                    'matched_terms': [], 'query_expansions': {}})
        hit['score'] = round(scores[source_id], 6)
        hit['retrieval_mode'] = 'hybrid'
        hits.append(hit)
    return hits


def search_with_mode(corpus: Corpus, query: str, limit: int = 5, topic: Topic | None = None,
                     institution: Institution = 'general') -> tuple[list[dict], str]:
    """Use verified local vectors when configured, otherwise report lexical fallback.

    Lexical evidence gates vector retrieval: no lexical overlap abstains. This is a
    conservative heuristic, not a guarantee of relevance or applicability.
    """
    entries = scoped_sources(corpus, institution)
    allowed = {s.id: s for s in entries if not topic or topic in s.topics}
    lexical = lexical_search(corpus, query, limit=len(entries), topic=topic, institution=institution)
    if lexical:
        # Never use an index built from a different in-memory corpus (e.g. test fixtures).
        if corpus.model_dump() == load_corpus().model_dump():
            from .vector_runtime import vector_rankings
            rankings = vector_rankings([query], institution)
            if rankings is not None:
                return fuse_rankings(lexical, rankings[0], allowed, limit), 'hybrid'
    return lexical[:limit], 'lexical'


def search(corpus: Corpus, query: str, limit: int = 5, topic: Topic | None = None,
           institution: Institution = 'general') -> list[dict]:
    return search_with_mode(corpus, query, limit, topic, institution)[0]
