"""Offline chunk index checks: .venv/bin/python verify_policy_chunk_index.py"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from frontrow.policy.chunk_index import ChunkIndex
from frontrow.policy.export import export_bundle


class ChunkIndexTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(tempfile.gettempdir()).resolve())
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.general = self.base / 'general'
        self.uaeu = self.base / 'uaeu'
        export_bundle(self.general)
        export_bundle(self.uaeu, institution='uaeu')

    def test_scope_and_matching_chunk_provenance(self):
        general = ChunkIndex(self.general)
        uaeu = ChunkIndex(self.uaeu, institution='uaeu')
        self.assertFalse(any(c['source'].startswith('uaeu-') for c in general.chunks))
        self.assertTrue(any(c['source'].startswith('uaeu-') for c in uaeu.chunks))
        hits = uaeu.search('UAEU student academic credit generative AI', limit=100)
        self.assertTrue(any(hit['source_institution'] == 'uaeu' for hit in hits))
        for hit in hits:
            chunk = next(c for c in uaeu.chunks if c['source'] == hit['source_file']
                         and c['chunk_id'] == hit['chunk_id'])
            self.assertEqual(hit['text'], chunk['text'])
            source = uaeu.manifest['sources'][chunk['source']]
            self.assertEqual((hit['source_id'], hit['source_url'], hit['source_scope']),
                             (source['id'], source['url'], source['scope']))
            self.assertGreater(hit['score'], 0)
        self.assertEqual(hits, uaeu.search('UAEU student academic credit generative AI', limit=100))

    def test_unknown_query_and_scope_mismatch_abstain(self):
        index = ChunkIndex(self.general)
        self.assertEqual(index.search('quasar xylophone marsupial'), [])
        self.assertEqual(index.search('the and'), [])
        with self.assertRaises(ValueError):
            ChunkIndex(self.uaeu, institution='general')
        for limit in (0, 101):
            with self.assertRaises(ValueError):
                index.search('privacy', limit)

    def test_partial_chunk_retains_source_and_corpus_caveats_in_cli(self):
        script = Path(__file__).resolve().parent / 'scripts' / 'search_policy_chunks.py'
        run = subprocess.run([sys.executable, str(script), 'transfer conditions',
                              '--bundle', str(self.general), '--limit', '10'],
                             capture_output=True, text=True, check=True)
        output = json.loads(run.stdout)
        manifest = json.loads((self.general / 'manifest.json').read_text(encoding='utf-8'))
        source = manifest['sources']['uae-personal-data-protection.md']
        partial = next(hit for hit in output['results']
                       if hit['source_id'] == source['id'] and hit['chunk_id'] == 1)
        self.assertTrue(partial['text'].endswith('government data and'))
        for field in ('verification', 'document_type', 'jurisdiction', 'published', 'retrieved', 'scope'):
            self.assertEqual(partial['source_' + field], source[field])
        self.assertIn('Full current text and amendments require further verification',
                      partial['source_verification'])
        self.assertEqual(output['corpus_limitations'], manifest['corpus_limitations'])
        self.assertTrue(any('cross-border transfer rules' in caveat
                            for caveat in output['corpus_limitations']))
        self.assertIn('excerpt', output['excerpt_notice'])
        self.assertIn('may omit or cut off', output['excerpt_notice'])

    def test_drift_is_rejected_before_indexing(self):
        (self.general / 'chunks.jsonl').write_text('{}\n', encoding='utf-8')
        with self.assertRaises(ValueError):
            ChunkIndex(self.general)


if __name__ == '__main__':
    unittest.main()
