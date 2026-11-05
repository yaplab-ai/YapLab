"""Verify real local vectors: run with the isolated vector environment Python."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

API = Path(__file__).resolve().parent
ROOT = API.parents[1]
SCRIPT = API / 'scripts/vector_policy_kb.py'
INDEXES = ROOT / 'knowledge-base/local-vector'
MODEL = Path(os.environ.get('YAPLAB_VECTOR_MODEL', '/tmp/yaplab-vector-model'))


class VectorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(tempfile.gettempdir()).resolve())
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)

    def run_search(self, scope, index, *, check=True):
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
        return subprocess.run([sys.executable, str(SCRIPT), 'search', '--institution', scope,
                               '--model-dir', str(MODEL), '--index-dir', str(index),
                               '--query', 'student academic credit generative AI', '--limit', '100'],
                              capture_output=True, text=True, env=env, check=check)

    def test_semantic_search_and_institution_scope(self):
        general = json.loads(self.run_search('general', INDEXES / 'general').stdout)
        uaeu = json.loads(self.run_search('uaeu', INDEXES / 'uaeu').stdout)
        self.assertEqual(general['retrieval'], 'local_minilm_normalized_faiss_inner_product')
        self.assertFalse(any(hit['source_institution'] == 'uaeu' for hit in general['results']))
        self.assertEqual(uaeu['results'][0]['source_id'], 'uaeu-student-generative-ai')
        self.assertTrue(all(hit['source_verification'] for hit in uaeu['results']))
        self.assertTrue(uaeu['corpus_limitations'])
        self.assertIn('excerpt', uaeu['excerpt_notice'])
        wrong_scope = self.run_search('general', INDEXES / 'uaeu', check=False)
        self.assertNotEqual(wrong_scope.returncode, 0)
        self.assertIn('scope or input hashes', wrong_scope.stderr)

    def test_changed_metadata_and_index_are_rejected(self):
        copied = self.base / 'index'
        shutil.copytree(INDEXES / 'general', copied)
        config_path = copied / 'config.json'
        config = json.loads(config_path.read_text())
        config['library_versions']['python'] = 'other-compatible-version'
        config_path.write_text(json.dumps(config), encoding='utf-8')
        self.assertTrue(json.loads(self.run_search('general', copied).stdout)['results'])
        metadata = copied / 'metadata.json'
        metadata.write_text(metadata.read_text() + ' ', encoding='utf-8')
        result = self.run_search('general', copied, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('hash differs', result.stderr)
        shutil.copyfile(INDEXES / 'general' / 'metadata.json', metadata)
        with (copied / 'faiss.index').open('ab') as stream:
            stream.write(b'drift')
        result = self.run_search('general', copied, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('hash differs', result.stderr)

    def test_current_bundle_and_model_drift_are_rejected(self):
        copied = self.base / 'knowledge-base/itu-reference/general'
        shutil.copytree(ROOT / 'knowledge-base/itu-reference/general', copied)
        program = """import importlib.util, pathlib, sys
spec = importlib.util.spec_from_file_location('vector_policy_kb', sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
base = pathlib.Path(sys.argv[2])
module.ROOT = base
module.bundle_data('general')
(base / 'knowledge-base/itu-reference/general/chunks.jsonl').write_text('{}\\n')
try:
    module.bundle_data('general')
except ValueError as exc:
    assert 'bundle failed exact corpus validation' in str(exc)
else:
    raise AssertionError('input drift accepted')
model = base / 'model/1_Pooling'
model.mkdir(parents=True)
(model / 'config.json').write_text('{}')
try:
    module.model_load(model.parent)
except ValueError as exc:
    assert 'model file differs' in str(exc)
else:
    raise AssertionError('model drift accepted')
"""
        subprocess.run([sys.executable, '-c', program, str(SCRIPT), str(self.base)],
                       capture_output=True, text=True, check=True,
                       env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))



if __name__ == '__main__':
    unittest.main()
