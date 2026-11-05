"""Offline launcher configuration and retrieval-reporting checks."""
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('hackathon_demo', Path(__file__).with_name('run-hackathon-demo.py'))
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)


class LauncherTest(unittest.TestCase):
    def test_defaults_require_complete_local_assets_and_do_not_override_explicit_settings(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            python = root / 'python'
            python.write_text('')
            python.chmod(0o755)
            model = root / 'model'
            model.mkdir()
            indexes = root / 'indexes'
            for scope in ('general', 'uaeu'):
                (indexes / scope).mkdir(parents=True)
                for name in ('config.json', 'metadata.json', 'faiss.index'):
                    (indexes / scope / name).touch()
            paths = tuple(map(str, (python, model, indexes)))
            env = {}
            self.assertEqual(demo.configure_vectors(env, root, paths), 'automatic local defaults')
            self.assertEqual(tuple(env[key] for key in demo.VECTOR_KEYS), paths)
            explicit = {demo.VECTOR_KEYS[0]: '/invalid/explicit-python'}
            self.assertEqual(demo.configure_vectors(explicit, root, paths), 'explicit settings')
            self.assertEqual(explicit, {demo.VECTOR_KEYS[0]: '/invalid/explicit-python'})
            (indexes / 'uaeu' / 'faiss.index').unlink()
            missing = {}
            self.assertEqual(demo.configure_vectors(missing, root, paths), 'local vector files unavailable')
            self.assertEqual(missing, {})

    def test_probe_reports_actual_mode_and_does_not_guess_on_error(self):
        for value in ('hybrid', 'lexical', 'unexpected'):
            with self.subTest(value=value), patch.object(demo, 'urlopen', return_value=io.BytesIO(json.dumps({'retrieval_mode': value}).encode())) as request:
                self.assertEqual(demo.retrieval_probe('http://127.0.0.1:8765', 'uaeu'), value if value != 'unexpected' else 'unknown')
                self.assertEqual(json.loads(request.call_args.args[0].data)['institution'], 'uaeu')
        with patch.object(demo, 'urlopen', side_effect=OSError('offline')):
            self.assertEqual(demo.retrieval_probe('http://127.0.0.1:8765', 'general'), 'unknown')


if __name__ == '__main__':
    unittest.main()
