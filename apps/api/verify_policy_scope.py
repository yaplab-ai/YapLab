"""Offline checks for the three independently verified policy scope boundaries."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from frontrow.policy.evidence import load_corpus, search, scoped_sources
from frontrow.server import create_app


class ScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.corpus = load_corpus()
        cls.sources = {entry.id: entry for entry in cls.corpus.entries}

    def test_tdra_reference_preserves_entity_and_service_scope(self):
        source = self.sources['uae-digital-accessibility-policy']
        self.assertEqual(source.document_type, 'government_policy')
        self.assertEqual(source.published, '2024-03')
        self.assertIn('Article 3', source.scope)
        self.assertIn('best efforts', source.scope)
        self.assertIn('private university is not established', source.scope)
        self.assertIn('public-service sites within that policy context', source.summary)
        self.assertIn('page 7', source.source_locator)
        self.assertIn('page 13', source.source_locator)
        self.assertIn('blanket applicability', ' '.join(source.limitations))
        found = search(self.corpus, 'WCAG 2.1 AA public-service sites digital accessibility', 3)
        self.assertEqual(found[0]['id'], source.id)

    def test_natural_wcag_review_prioritizes_scoped_source(self):
        text = ('Our university rehearsal website needs captions and keyboard access. '
                'Does citing WCAG establish that our private university is compliant?')
        with patch.dict('os.environ', {'FRONTROW_LLM': 'fake', 'FRONTROW_TTS': 'none',
                'FRONTROW_STT': 'none', 'FRONTROW_POLICY_LLM': 'off', 'FRONTROW_POLICY_COORDINATION': 'off'}):
            with TestClient(create_app()) as client:
                response = client.post('/policy/review', json={'text': text})
        self.assertEqual(response.status_code, 200)
        result = response.json()
        accessibility = next(item for item in result['considerations'] if item['topic'] == 'accessibility')
        self.assertEqual(accessibility['citations'][0]['id'], 'uae-digital-accessibility-policy')
        self.assertIn('private university is not established', accessibility['citations'][0]['scope'])
        self.assertIn('before asserting applicability', accessibility['recommendation'])
        self.assertIn('wcag', result['audit']['matched_terms'])
        self.assertEqual(result['audit']['retrieval_records'][0]['source_selection'], 'explicit_wcag_match')
        self.assertTrue(any('not a compliance assessment' in item for item in result['limitations']))
        self.assertEqual(result['review_mode'], 'deterministic')

    def test_ethics_principles_are_distinct_voluntary_guidance(self):
        source = self.sources['uae-ai-ethics-principles-guidelines']
        self.assertEqual(source.document_type, 'guidance')
        self.assertEqual(source.published, '2022-12')  # cover, not URL upload date
        for boundary in ('Non-binding', 'significant decisions', 'critical decisions',
                         'ordinary teaching rehearsal', 'voluntary design reference'):
            self.assertIn(boundary, source.scope)
        self.assertIn('Section 1.1', source.source_locator)
        self.assertIn('section 1.2', source.source_locator)
        self.assertNotEqual(source.url, self.sources['uae-ai-ethics-self-assessment'].url)
        self.assertIn('section 1.2', ' '.join(self.sources['uae-ai-ethics-self-assessment'].limitations))

    def test_uaeu_student_policy_does_not_become_staff_or_national_rule(self):
        source = self.sources['uaeu-student-generative-ai']
        self.assertEqual(source.institution, 'uaeu')
        self.assertIn('students', source.scope)
        self.assertIn('academic credit', source.scope)
        self.assertIn('generic staff-rehearsal', source.scope)
        self.assertIn('page 2', source.source_locator)
        self.assertNotIn(source.id, {s.id for s in scoped_sources(self.corpus)})
        self.assertIn(source.id, {s.id for s in scoped_sources(self.corpus, 'uaeu')})

    def test_accessible_policy_pdfs_do_not_verify_statutory_privacy_text(self):
        source = self.sources['uae-personal-data-protection']
        self.assertIn('403', source.verification)
        self.assertIn('Full current text', source.verification)
        self.assertIn('cross-border transfer conditions', ' '.join(source.limitations))
        self.assertIn('not been verified', ' '.join(source.limitations))
        self.assertTrue(any('PDPL statutory text' in x for x in self.corpus.limitations))

    def test_api_and_review_expose_scope_without_inferred_institution(self):
        with patch.dict('os.environ', {'FRONTROW_LLM': 'fake', 'FRONTROW_TTS': 'none',
                'FRONTROW_STT': 'none', 'FRONTROW_POLICY_LLM': 'off', 'FRONTROW_POLICY_COORDINATION': 'off'}):
            with TestClient(create_app()) as client:
                general = client.get('/policy/sources').json()
                self.assertEqual(general['version'], '2026-11-04.4')
                self.assertEqual(len(general['entries']), 10)
                self.assertEqual(len(client.get('/policy/sources?institution=uaeu').json()['entries']), 13)
                response = client.post('/policy/review', json={'text': 'WCAG 2.1 AA accessibility on a private university website', 'topics': ['accessibility']})
                self.assertEqual(response.status_code, 200)
                result = response.json()
                refs = [s for item in result['considerations'] for s in item['citations']]
                tdra = next(s for s in refs if s['id'] == 'uae-digital-accessibility-policy')
                self.assertIn('private university is not established', tdra['scope'])
                self.assertEqual(result['review_mode'], 'deterministic')


if __name__ == '__main__':
    unittest.main()
