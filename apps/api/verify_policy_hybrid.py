"""Local retrieval fallback, fusion, filters and mode regressions."""
import unittest
from unittest.mock import patch

from frontrow.policy.evidence import load_corpus, search_with_mode


class HybridTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.corpus = load_corpus()

    def test_fallback_and_abstention(self):
        with patch('frontrow.policy.vector_runtime.vector_rankings', return_value=None):
            hits, mode = search_with_mode(self.corpus, 'personal data privacy')
            self.assertTrue(hits)
            self.assertEqual(mode, 'lexical')
            hits, mode = search_with_mode(self.corpus, 'quasar xylophone marsupial')
            self.assertEqual((hits, mode), ([], 'lexical'))

    def test_missing_worker_falls_back(self):
        settings = {'FRONTROW_POLICY_VECTOR_PYTHON': '/missing/local/python',
                    'FRONTROW_POLICY_VECTOR_MODEL': '/missing/model',
                    'FRONTROW_POLICY_VECTOR_INDEX_ROOT': '/missing/index'}
        with patch.dict('os.environ', settings):
            hits, mode = search_with_mode(self.corpus, 'personal data privacy')
        self.assertTrue(hits)
        self.assertEqual(mode, 'lexical')

    def test_hybrid_filters_institution_and_topic(self):
        ids = ['uaeu-student-generative-ai', 'uae-personal-data-protection', 'forged-source']
        with patch('frontrow.policy.vector_runtime.vector_rankings', return_value=[ids]):
            general, mode = search_with_mode(self.corpus, 'personal data privacy', limit=100, topic='privacy')
            self.assertEqual(mode, 'hybrid')
            self.assertNotIn(ids[0], [h['id'] for h in general])
            self.assertNotIn(ids[2], [h['id'] for h in general])
            self.assertTrue(all('privacy' in h['topics'] and h['retrieval_mode'] == 'hybrid' for h in general))
            self.assertTrue(all(h['scope'] and h['limitations'] for h in general))
            uaeu, mode = search_with_mode(self.corpus, 'personal data privacy', limit=100, institution='uaeu')
            self.assertEqual(mode, 'hybrid')
            self.assertIn(ids[0], [h['id'] for h in uaeu])

    def test_fixture_cannot_use_unrelated_index(self):
        fixture = self.corpus.model_copy(update={'entries':self.corpus.entries[:1]})
        with patch('frontrow.policy.vector_runtime.vector_rankings') as worker:
            _, mode = search_with_mode(fixture, 'personal data privacy')
            self.assertEqual(mode, 'lexical')
            worker.assert_not_called()

if __name__ == '__main__':
    unittest.main()
