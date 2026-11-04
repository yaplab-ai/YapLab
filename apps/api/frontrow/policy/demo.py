"""Scripted, network-free selections for the synthetic coordination demo.

The coordinator still validates every returned ID against each role's released
facts and retrieved source notes. Nothing in these selections is legal advice.
"""
from __future__ import annotations

import json

from frontrow.llm.base import LLMClient

# Ordered most specific first; each tuple is an action and a supporting fact
# whose ID must be present in that role's released view.
_CHOICES = {
    'caption-failure': {
        'teacher': (('resume_vendor_workshop', 'cf-2b'), ('delay_workshop', 'cf-1a')),
        'privacy': (('verify_vendor_terms', 'cf-2b'), ('protect_attendee_identity', 'cf-1c')),
        'accessibility': (('confirm_accessible_option', 'cf-2c'), ('identify_access_needs', 'cf-1c')),
    },
    'transcript-disclosure': {
        'teacher': (('pause_transcript_sharing', 'td-1b'),),
        'privacy': (('review_transcript_access', 'td-1b'),),
        'accessibility': (('offer_private_support', 'td-1c'),),
    },
    'feedback-as-grade': {
        'teacher': (('clarify_practice_feedback', 'fg-1b'),),
        'privacy': (('check_feedback_data', 'fg-2c'), ('check_feedback_data', 'fg-1a')),
        'accessibility': (('check_feedback_access', 'fg-1c'),),
    },
}
_PREFERRED_SOURCES = {
    ('caption-failure', 'teacher'): ('uae-digital-accessibility-policy', 'uae-persons-with-disabilities-education'),
    ('caption-failure', 'accessibility'): ('uae-persons-with-disabilities-education', 'uae-digital-accessibility-policy'),
    ('feedback-as-grade', 'teacher'): ('england-generative-ai-education', 'unesco-generative-ai-education'),
    ('feedback-as-grade', 'accessibility'): ('uae-digital-accessibility-policy', 'uae-persons-with-disabilities-education'),
    ('transcript-disclosure', 'accessibility'): ('uae-persons-with-disabilities-education', 'uae-digital-accessibility-policy'),
}


class PolicyDemoLLM(LLMClient):
    """Select IDs deterministically from the supplied role request only."""

    async def complete(self, system: str, user: str, *, model: str, timeout: float) -> str:
        payload = json.loads(user)
        role, scenario = payload['role'], payload['scenario_id']
        ids = payload['allowed_ids']
        candidates = _CHOICES.get(scenario, {}).get(role, ())
        source_preferences = _PREFERRED_SOURCES.get((scenario, role), ('uae-personal-data-protection',))
        source = next((item for item in source_preferences if item in ids['source_ids']), None)
        if source is None:
            return json.dumps({'proposals': [], 'questions': []})
        for action, fact in candidates:
            if action in ids['action_ids'] and fact in ids['fact_ids']:
                return json.dumps({'proposals': [{'action_id': action, 'fact_ids': [fact],
                                                  'source_ids': [source]}], 'questions': []})
        return json.dumps({'proposals': [], 'questions': []})
