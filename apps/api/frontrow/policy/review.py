"""Deterministic retrieval-based prompts for human review, not compliance verdicts."""
from __future__ import annotations

from .evidence import Corpus, Institution, Topic, query_expansions, scoped_sources, search, tokens

_LABELS = {
    'privacy': 'Privacy and personal data',
    'accessibility': 'Accessibility and inclusion',
    'responsible_ai': 'Responsible AI',
    'education': 'Education',
    'human_oversight': 'Human oversight',
}
# Cues identify a topic for further investigation; they do not diagnose a problem.
_CUES = {
    'privacy': {'privacy', 'personal', 'student', 'pupil', 'data', 'consent', 'recording'},
    'accessibility': {'accessibility', 'accessible', 'disability', 'disabled', 'inclusive', 'inclusion', 'caption', 'captions'},
    'responsible_ai': {'artificial', 'algorithm', 'generative', 'model', 'chatbot', 'bias'},
    'education': {'education', 'educational', 'teaching', 'teacher', 'classroom', 'school', 'learning'},
    'human_oversight': {'human', 'oversight', 'supervision', 'supervised', 'review', 'teacher'},
}
_LIMITATIONS = [
    'This is a deterministic keyword-based starting point, not a compliance assessment or legal advice.',
    'A keyword match does not establish whether a safeguard is present, absent, adequate, or applicable.',
    'Check the original sources, current local requirements, and the facts with qualified reviewers.',
    'Do not submit personal, student-identifying, or confidential information; automatic checks cannot detect all such data.',
]


# Topic anchors guide ranking and requirement selection; they do not establish
# applicability. Curated vocabulary is auditable and deliberately small.
_TOPIC_TERMS = {
    'privacy': {'privacy', 'personal', 'data', 'identifiable', 'information', 'processing', 'consent', 'security', 'retention', 'transfer'},
    'accessibility': {'accessibility', 'accessible', 'disability', 'disabilities', 'access', 'inclusive', 'inclusion', 'caption', 'captions', 'support'},
    'responsible_ai': {'artificial', 'intelligence', 'ai', 'bias', 'fairness', 'ethics', 'accountability', 'risks', 'generated'},
    'education': {'education', 'educational', 'teaching', 'teacher', 'learning', 'learner', 'classroom', 'assessment'},
    'human_oversight': {'human', 'oversight', 'review', 'educator', 'teacher', 'check', 'supervision', 'accuracy'},
}
_TOPIC_ANCHORS = {
    'privacy': 'privacy personal data',
    'accessibility': 'accessibility disability',
    'responsible_ai': 'artificial intelligence ethics',
    'education': 'education teaching learning',
    'human_oversight': 'human oversight educator review',
}


def topic_query(query: str, topic: Topic) -> str:
    words = tokens(query)
    for terms in query_expansions(query).values():
        words.update(terms)
    return _TOPIC_ANCHORS[topic] + ' ' + ' '.join(sorted(words & _TOPIC_TERMS[topic]))


def requirement_index(source: dict, topic: Topic) -> int | None:
    requirements = source['requirements']
    if not requirements:
        return None
    terms = _TOPIC_TERMS[topic]
    return max(range(len(requirements)), key=lambda i: (len(tokens(requirements[i]) & terms), -i))


def review(corpus: Corpus, text: str, topics: list[Topic], context: str = '',
           institution: Institution = 'general') -> dict:
    entries = scoped_sources(corpus, institution)
    query = f'{text} {context}'.strip()
    words = tokens(query)
    expansions = query_expansions(query)
    words.update(term for terms in expansions.values() for term in terms)
    selected = list(dict.fromkeys(topics)) if topics else [
        topic for topic, cues in _CUES.items() if words & cues
    ]
    considerations = []
    gaps = []
    audit_sources = []
    audit_terms = set()
    audit_requirements = []
    for topic in selected:
        hits = search(corpus, topic_query(query, topic), limit=3, topic=topic, institution=institution)
        if not hits:
            # Explicitly selected topics can be explored even if no input word
            # occurs in the source; this is identified as a topic-only match.
            if topic in topics:
                sources = [s for s in entries if topic in s.topics][:2]
                hits = [{**s.model_dump(), 'matched_terms': [], 'score': 0.0} for s in sources]
            if not hits:
                gaps.append(f'No source in this collection matched {_LABELS[topic].lower()} and the supplied wording; consult additional sources.')
                continue
        source = hits[0]
        audit_sources.append(source['id'])
        audit_terms.update(source['matched_terms'])
        chosen_index = requirement_index(source, topic)
        if chosen_index is not None:
            audit_requirements.append({'topic': topic, 'source_id': source['id'], 'requirement_index': chosen_index})
        recommendation = (f"Review the source guidance in its stated scope: {source['requirements'][chosen_index]}"
                          if chosen_index is not None else
                          'Review the linked source and its stated scope for relevant guidance.')
        considerations.append({
            'topic': topic,
            'observation': (f"{_LABELS[topic]} was selected for investigation "
                            + ('by topic choice.' if not source['matched_terms'] else 'using matching terms.')),
            'recommendation': recommendation,
            'citations': [{k: v for k, v in source.items() if k not in {'score', 'matched_terms', 'query_expansions'}}],
        })
    if not selected:
        gaps.append('No supported topic was identified from the supplied wording. Select a topic or add non-personal context.')
    gaps.append('The supplied text alone cannot establish applicability, implementation details, or whether any requirement is met.')
    return {
        'review_mode': 'deterministic',
        'summary': ('Relevant source notes were found for human investigation.' if considerations
                    else 'No source-backed consideration was identified from the supplied wording.'),
        'considerations': considerations,
        'gaps': gaps,
        'limitations': list(dict.fromkeys(_LIMITATIONS + corpus.limitations + ([
            'UAEU materials are an institutional reference case; selecting them does not establish affiliation or applicability.'
        ] if institution == 'uaeu' else []))),
        'audit': {'corpus_version': corpus.version, 'institution': institution, 'source_ids': list(dict.fromkeys(audit_sources)),
                  'matched_terms': sorted(audit_terms), 'query_expansions': expansions, 'selected_topics': selected,
                  'topic_query_terms': {topic: sorted(tokens(topic_query(query, topic))) for topic in selected},
                  'selected_requirements': audit_requirements,
                  'selection_mode': 'requested_topics' if topics else 'keyword_cues',
                  'retrieval': 'weighted_lexical', 'requirement_selection': 'topic_vocabulary_overlap', 'review_mode': 'deterministic'},
    }
