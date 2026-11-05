"""Offline tests of the bounded app HTTP evaluation driver."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

path = Path(__file__).parent / 'scripts/evaluate_policy_app.py'
spec = importlib.util.spec_from_file_location('evaluate_policy_app', path)
driver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)


def encoded(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode()


class FakeTransport:
    def __init__(self, output, *, fail_coordinate=False, wrong_model=False, provider='nebius', protocol='4'):
        self.output = output
        self.fail_coordinate = fail_coordinate
        self.wrong_model = wrong_model
        self.provider = provider
        self.protocol = protocol
        self.calls = []
        self.by_id = {}
        self.number = 0
        self.coordination_calls = 0
        self.saved_bytes = {}

    def request(self, method, path, body=None):
        self.calls.append((method, path, body))
        if path == '/policy/coordination/status':
            return encoded({'enabled': True, 'review_mode': 'model_assisted',
                            'model': 'wrong' if self.wrong_model else driver.MODEL,
                            'provider': self.provider, 'protocol_version': self.protocol})
        if path == '/policy/sources?institution=general':
            return encoded({'version': driver.CORPUS_VERSION})
        if path == '/policy/exercises?role=teacher':
            self.number += 1
            exercise = 'exercise' + str(self.number)
            self.by_id[exercise] = {'scenario': body['scenario_id'], 'stage': 1}
            return self.view(exercise)
        parts = path.split('/')
        exercise = parts[3]
        state = self.by_id[exercise]
        suffix = parts[4]
        if suffix.startswith('advance'):
            self.assert_previous(body, state)
            state['stage'] += 1
            return self.view(exercise)
        if suffix == 'coordinate':
            self.coordination_calls += 1
            checkpoint = json.loads((self.output / 'manifest.json').read_bytes())
            assert checkpoint['reserved_provider_attempts'] == 3 * self.coordination_calls
            assert checkpoint['uncertain_outcome'] and checkpoint['in_flight']['reserved'] == 3
            if self.fail_coordinate:
                raise TimeoutError('do not expose raw exception text')
            return encoded({'scenario_id': state['scenario'], 'stage': state['stage'], 'review_mode': 'model_assisted',
                            'protocol_version': '4', 'corpus_version': driver.CORPUS_VERSION,
                            'model': {'provider': 'nebius', 'model': driver.MODEL}, 'roles': [
                                {'role': role, 'status': 'completed', 'prompt_attempted': True,
                                 'prompt_sha256': 'hash', 'usage': {'prompt_tokens': 100, 'completion_tokens': 20},
                                 'latency_ms': 12, 'provider_status': 'success', 'proposals': []}
                                for role in driver.ROLES]})
        if suffix == 'decision':
            fact, text = driver.DECISIONS[state['scenario']]
            assert body == {'role': 'teacher', 'decision': text, 'source_ids': [fact], 'expected_stage': state['stage']}
            return b'{"ok":true}'
        if suffix == 'timeline':
            data = encoded({'scenario_id': state['scenario'], 'current_stage': state['stage'], 'events': [], 'sha256': 'hash'})
            self.saved_bytes[(state['scenario'], state['stage'], 'json')] = data
            return data
        if suffix == 'timeline.html':
            data = ('<html>synthetic ' + state['scenario'] + ' ' + str(state['stage']) + '</html>').encode()
            self.saved_bytes[(state['scenario'], state['stage'], 'html')] = data
            return data
        raise AssertionError('unexpected request')

    def assert_previous(self, body, state):
        assert body == {'expected_stage': state['stage']}

    def view(self, exercise):
        state = self.by_id[exercise]
        fact = driver.DECISIONS[state['scenario']][0]
        return encoded({'exercise_id': exercise, 'scenario_id': state['scenario'], 'current_stage': state['stage'],
                        'released_stages': [{'facts': [{'id': fact}]}]})


class DriverTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.output = Path(self.tmp.name) / 'new-evidence'
        self.provenance = {'source_commit': 'test', 'code_sha256': 'test'}

    def test_dry_run_no_network_and_explicit_execution_required(self):
        with patch.object(driver, 'HTTPTransport', side_effect=AssertionError('network attempted')):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(driver.main([]), 0)
                self.assertEqual(driver.main(['--api-url', 'http://127.0.0.1:8000']), 0)
        self.assertFalse(self.output.exists())
        for url in ('http://example.com', 'http://127.0.0.1@evil.example', 'http://127.0.0.1/x', 'file:///tmp/a'):
            with self.assertRaises(ValueError): driver.loopback_url(url)

    def test_complete_run_persists_exact_exports_and_cost(self):
        transport = FakeTransport(self.output)
        manifest = driver.Driver(transport, self.output, 'authorized synthetic evaluation', self.provenance).run()
        self.assertEqual(transport.coordination_calls, 9)
        self.assertEqual(manifest['reserved_provider_attempts'], 27)
        self.assertEqual(len(manifest['role_results']), 27)
        self.assertEqual(len(manifest['completed_stages']), 9)
        self.assertEqual(manifest['run_status'], 'completed')
        self.assertEqual(manifest['cost_estimate']['estimated_observed_usd'], '0.0002916')
        self.assertTrue(manifest['cost_estimate']['complete'])
        self.assertFalse(manifest['cost_estimate']['invoice'])
        self.assertFalse(manifest['cost_estimate']['invoice_verified'])
        for (scenario, stage, ext), data in transport.saved_bytes.items():
            self.assertEqual((self.output / f'{scenario}-stage-{stage}.{ext}').read_bytes(), data)
            if stage == 3:
                self.assertEqual((self.output / f'{scenario}.{ext}').read_bytes(), data)
        self.assertEqual(json.loads((self.output / 'manifest.json').read_bytes()), manifest)
        with self.assertRaises(FileExistsError):
            driver.Driver(transport, self.output, 'approved', self.provenance).run()

    def test_real_app_routes_with_offline_mock_provider(self):
        # Exercise the exact FastAPI routes used by the UI without network calls.
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from frontrow.llm.openai_client import OpenAIClient
        from frontrow.policy.router import create_router
        from frontrow.policy.scenarios import router as scenario_router
        from verify_policy_coordination import Scripted

        class MockDirect(OpenAIClient):
            def __init__(self):
                self.provider_name = 'nebius'
                self.scripted = Scripted()
            async def complete(self, system, user, *, model, timeout):
                return await self.scripted.complete(system, user, model=model, timeout=timeout)
        provider = MockDirect()
        app = FastAPI()
        app.include_router(scenario_router)
        with patch.dict('os.environ', {'FRONTROW_POLICY_EVALUATION_CALL_LIMIT': '60'}):
            app.include_router(create_router(coordination_llm=provider, coordination_model=driver.MODEL,
                                             coordination_mode='model_assisted'))
        client = TestClient(app)
        class TestClientTransport:
            def request(self, method, path, body=None):
                response = client.request(method, path, json=body)
                if response.status_code >= 400:
                    raise AssertionError(f'Unexpected app status {response.status_code} at {path}')
                return response.content
        result = driver.Driver(TestClientTransport(), self.output, 'offline mock', self.provenance).run()
        self.assertEqual(result['run_status'], 'completed')
        self.assertEqual(len(provider.scripted.requests), 27)
        self.assertEqual(result['cost_estimate']['missing_usage_attempts'], 27)
        self.assertFalse(result['cost_estimate']['complete'])
        for scenario in driver.SCENARIOS:
            audit = json.loads((self.output / f'{scenario}.json').read_bytes())
            self.assertEqual(audit['current_stage'], 3)
            self.assertEqual(len(audit['rounds']), 3)
            self.assertEqual(sum(event['type'] == 'decision' for event in audit['events']), 3)

    def test_timeout_stops_and_keeps_unknown_reserved_attempts(self):
        transport = FakeTransport(self.output, fail_coordinate=True)
        with self.assertRaises(TimeoutError):
            driver.Driver(transport, self.output, 'approved', self.provenance).run()
        state = json.loads((self.output / 'manifest.json').read_text())
        self.assertEqual(transport.coordination_calls, 1)
        self.assertEqual(state['reserved_provider_attempts'], 3)
        self.assertTrue(state['uncertain_outcome'])
        self.assertEqual(state['stopped_phase'], 'coordinate')
        self.assertFalse(state['cost_estimate']['complete'])
        self.assertNotIn('do not expose', json.dumps(state))

    def test_preflight_and_reservation_limit_stop_before_additional_calls(self):
        transport = FakeTransport(self.output, wrong_model=True)
        with self.assertRaises(ValueError): driver.Driver(transport, self.output, 'approved', self.provenance).run()
        self.assertEqual(transport.coordination_calls, 0)
        for index, kwargs in enumerate(({'provider': 'other'}, {'protocol': '3'}, {'provider': None}, {'protocol': None})):
            target = Path(self.tmp.name) / f'bad-preflight-{index}'
            rejected = FakeTransport(target, **kwargs)
            with self.assertRaises(ValueError):
                driver.Driver(rejected, target, 'approved', self.provenance).run()
            self.assertEqual(rejected.coordination_calls, 0)
        self.output = Path(self.tmp.name) / 'other-evidence'
        transport = FakeTransport(self.output)
        with patch.object(driver, 'MAX_CALLS', 6):
            with self.assertRaises(ValueError): driver.Driver(transport, self.output, 'approved', self.provenance).run()
        self.assertEqual(transport.coordination_calls, 2)
        state = json.loads((self.output / 'manifest.json').read_text())
        self.assertEqual(state['reserved_provider_attempts'], 6)
        self.assertFalse(state['uncertain_outcome'])


if __name__ == '__main__': unittest.main()
