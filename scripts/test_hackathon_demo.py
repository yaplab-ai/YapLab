"""Offline launcher configuration and retrieval-reporting checks."""
import contextlib
import importlib.util
import os
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
    def test_live_missing_key_stops_before_socket_or_process(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(demo, 'ROOT', Path(tmp)), \
             patch.dict(os.environ, {}, clear=True), patch('sys.argv', ['launcher', '--live']), \
             patch.object(demo.socket, 'socket') as socket, patch.object(demo.subprocess, 'Popen') as popen:
            output = io.StringIO()
            with contextlib.redirect_stderr(output):
                self.assertEqual(demo.main(), 1)
            self.assertIn('requires NEBIUS_API_KEY', output.getvalue())
            socket.assert_not_called()
            popen.assert_not_called()

    def test_key_env_precedes_dotenv_and_empty_env_does_not_fall_back(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'apps/api').mkdir(parents=True)
            (root / 'apps/api/.venv').symlink_to(demo.ROOT / 'apps/api/.venv')
            (root / '.env').write_text("export NEBIUS_API_KEY='file-test-value' # comment\n")
            with patch.dict(os.environ, {}, clear=True):
                self.assertEqual(demo.nebius_key({}, root), 'file-test-value')
            self.assertEqual(demo.nebius_key({'NEBIUS_API_KEY': 'environment-test-value'}, root), 'environment-test-value')
            self.assertIsNone(demo.nebius_key({'NEBIUS_API_KEY': ''}, root))
            self.assertIsNone(demo.nebius_key({'NEBIUS_API_KEY': '   '}, root))

    def test_live_environment_caps_policy_and_pins_all_model_routes(self):
        args = demo.parse_args(['--live', '--max-model-calls', '36'])
        env = {'NEBIUS_API_KEY': 'test-key', 'FRONTROW_LLM_MODEL_FAST': 'old-fast',
               'FRONTROW_LLM_MODEL_REASONING': 'old-reasoning', 'FRONTROW_POLICY_REPLAY_PATH': 'old-recording'}
        demo.configure_mode(env, args, 'http://api', 'http://ui')
        self.assertEqual(env['FRONTROW_LLM'], 'nebius')
        self.assertEqual(env['FRONTROW_POLICY_LLM'], 'off')
        self.assertEqual(env['FRONTROW_POLICY_COORDINATION'], 'configured')
        self.assertEqual(env['FRONTROW_POLICY_EVALUATION_CALL_LIMIT'], '36')
        for name in ('FRONTROW_LLM_MODEL', 'FRONTROW_LLM_MODEL_FAST', 'FRONTROW_LLM_MODEL_REASONING'):
            self.assertEqual(env[name], demo.LIVE_MODEL)
        self.assertEqual(env['VITE_HACKATHON_DEMO'], '0')
        self.assertEqual(env['VITE_POLICY_REPLAY'], '0')
        self.assertEqual((env['FRONTROW_TTS'], env['FRONTROW_STT']), ('none', 'none'))
        self.assertNotIn('FRONTROW_POLICY_REPLAY_PATH', env)
        description = demo.mode_description(args)
        self.assertIn('synthetic facts only', description)
        self.assertIn('up to 3 model requests', description)
        self.assertIn('resets on process restart', description)
        self.assertIn('outside this policy coordination cap', description)
        self.assertNotIn('test-key', description)

    def test_limits_and_incompatible_modes(self):
        self.assertEqual(demo.parse_args(['--live']).max_model_calls, 27)
        for value in ('1', '60'):
            self.assertEqual(demo.parse_args(['--max-model-calls', value]).max_model_calls, int(value))
        for argv in (['--max-model-calls', '0'], ['--max-model-calls', '61'],
                     ['--max-model-calls', 'not-a-number'], ['--live', '--replay-live', 'recording.json']):
            with self.subTest(argv=argv), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                demo.parse_args(argv)

    def test_offline_and_replay_environment_preserves_default_behavior(self):
        args = demo.parse_args([])
        env = {'FRONTROW_POLICY_REPLAY_PATH': 'old', 'SOME_OTHER_SETTING': 'retained'}
        demo.configure_mode(env, args, 'http://api', 'http://ui')
        self.assertEqual(env, {'SOME_OTHER_SETTING': 'retained', 'FRONTROW_LLM': 'fake',
            'FRONTROW_POLICY_LLM': 'off', 'FRONTROW_POLICY_COORDINATION': 'demo',
            'FRONTROW_TTS': 'none', 'FRONTROW_STT': 'none', 'FRONTROW_TICK_INTERVAL_SECONDS': '3',
            'FRONTROW_MODERATOR_WARMUP_SECONDS': '0', 'FRONTROW_MODERATOR_WARMUP_MIN_WORDS': '0',
            'FRONTROW_CORS_ORIGINS': 'http://ui', 'VITE_API_URL': 'http://api',
            'VITE_HACKATHON_DEMO': '1', 'PYTHONUNBUFFERED': '1', 'VITE_POLICY_REPLAY': '0'})
        self.assertIn('scripted role proposals', demo.mode_description(args))
        with tempfile.TemporaryDirectory() as tmp:
            recording = Path(tmp) / 'recording.json'
            recording.touch()
            replay = demo.parse_args(['--replay-live', str(recording)])
            demo.configure_mode(env, replay, 'http://api', 'http://ui')
            self.assertEqual(env['VITE_POLICY_REPLAY'], '1')
            self.assertEqual(env['FRONTROW_POLICY_REPLAY_PATH'], str(recording.resolve()))
            self.assertIn('no new model calls', demo.mode_description(replay))

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
