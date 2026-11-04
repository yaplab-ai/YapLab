"""End-to-end offline scripted policy demo tests; no provider calls."""
from __future__ import annotations

import asyncio
import json
import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from frontrow.policy.demo import PolicyDemoLLM
from frontrow.policy.coordination import coordinate
from frontrow.policy.evidence import load_corpus
from verify_policy_coordination import snapshot
from frontrow.server import create_app
import frontrow.server as server


ENV = {'FRONTROW_POLICY_COORDINATION': 'demo', 'FRONTROW_POLICY_LLM': 'off',
       'FRONTROW_LLM': 'fake', 'FRONTROW_TTS': 'none', 'FRONTROW_STT': 'none'}


class RecordingDemo(PolicyDemoLLM):
    calls = []
    async def complete(self, system, user, *, model, timeout):
        self.calls.append((json.loads(user), model))
        return await super().complete(system, user, model=model, timeout=timeout)


class DemoTests(unittest.TestCase):
    def setUp(self):
        RecordingDemo.calls = []

    def test_offline_http_demo_has_stage_isolation_and_handoffs(self):
        with patch.dict(os.environ, ENV), \
             patch('frontrow.policy.demo.PolicyDemoLLM', RecordingDemo), \
             patch('frontrow.server.OpenAIClient') as network, \
             patch('frontrow.server.FallbackLLM') as fallback, \
             patch('frontrow.server._tts_from_env', wraps=server._tts_from_env) as tts, \
             patch('frontrow.server._stt_from_env', wraps=server._stt_from_env) as stt:
            with TestClient(create_app()) as client:
                status = client.get('/policy/coordination/status')
                self.assertEqual(status.status_code, 200)
                self.assertEqual(status.json(), {'enabled': True, 'review_mode': 'offline_test', 'model': 'scripted-demo'})
                created = client.post('/policy/exercises?role=teacher', json={'scenario_id': 'caption-failure'})
                self.assertEqual(created.status_code, 200)
                exercise = created.json()['exercise_id']
                url = f'/policy/exercises/{exercise}/coordinate'
                first = client.post(url, json={'expected_stage': 1, 'institution': 'general'})
                self.assertEqual(first.status_code, 200)
                first_calls = list(RecordingDemo.calls)
                self.assertEqual(len(first_calls), 3)
                self.assertTrue(all(call[0]['stage'] == 1 for call in first_calls))
                self.assertTrue(all(not any(fact['id'].startswith('cf-2') or fact['id'].startswith('cf-3')
                                            for fact in call[0]['facts']) for call in first_calls))
                self.assertTrue(all(proposal['action_id'] != 'resume_vendor_workshop'
                                    for role in first.json()['roles'] for proposal in role['proposals']))
                advanced = client.post(f'/policy/exercises/{exercise}/advance?role=teacher', json={'expected_stage': 1})
                self.assertEqual(advanced.status_code, 200)
                second = client.post(url, json={'expected_stage': 2, 'institution': 'general'})
                self.assertEqual(second.status_code, 200)
                result = second.json()
                self.assertEqual(result['review_mode'], 'offline_test')
                self.assertEqual(result['model'], {'provider': 'offline_test', 'model': 'scripted-demo'})
                self.assertEqual(len(RecordingDemo.calls), 6)
                self.assertTrue(all(model == 'scripted-demo' for _, model in RecordingDemo.calls))
                stage_calls = {payload['role']: payload for payload, _ in RecordingDemo.calls[3:]}
                self.assertEqual(set(stage_calls), {'teacher', 'privacy', 'accessibility'})
                actions = {'teacher': 'resume_vendor_workshop', 'privacy': 'verify_vendor_terms',
                           'accessibility': 'confirm_accessible_option'}
                for role in result['roles']:
                    self.assertEqual(role['status'], 'completed')
                    self.assertEqual(role['proposals'][0]['action_id'], actions[role['role']])
                    proposal = role['proposals'][0]
                    self.assertTrue(set(proposal['fact_ids']) <= set(stage_calls[role['role']]['allowed_ids']['fact_ids']))
                    self.assertTrue(set(proposal['source_ids']) <= set(stage_calls[role['role']]['allowed_ids']['source_ids']))
                    self.assertTrue(set(proposal['source_ids']) <= {source['id'] for source in role['evidence']})
                plan = {item['action_id']: item for item in result['plan']}
                self.assertEqual(set(plan['resume_vendor_workshop']['depends_on']),
                                 {'verify_vendor_terms', 'confirm_accessible_option'})
                self.assertEqual(plan['resume_vendor_workshop']['status'], 'awaiting_human_confirmation')
                cached = client.post(url, json={'expected_stage': 2, 'institution': 'general'})
                self.assertEqual(cached.status_code, 200)
                self.assertEqual(len(RecordingDemo.calls), 6)
            network.assert_not_called()
            fallback.assert_not_called()
            tts.assert_called_once_with('none')
            stt.assert_called_once_with('none')

    def test_all_scenarios_have_supported_offline_selections(self):
        async def run():
            for scenario in ('caption-failure', 'transcript-disclosure', 'feedback-as-grade'):
                for stage in (1, 2):
                    result = await coordinate(load_corpus(), snapshot(scenario, stage), PolicyDemoLLM(),
                                              'scripted-demo', mode='offline_test')
                    self.assertEqual(result['review_mode'], 'offline_test')
                    for role in result['roles']:
                        self.assertEqual(role['status'], 'completed')
                        self.assertTrue(role['proposals'])
        asyncio.run(run())

    def test_demo_rejects_provider_configuration_before_construction(self):
        for key, value in [('FRONTROW_LLM', 'nebius'), ('FRONTROW_TTS', 'elevenlabs'),
                           ('FRONTROW_STT', 'elevenlabs'), ('FRONTROW_POLICY_LLM', 'configured')]:
            settings = {**ENV, key: value}
            with self.subTest(key=key), patch.dict(os.environ, settings), \
                 patch('frontrow.server.llm_from_env') as factory, \
                 patch('frontrow.server._tts_from_env') as tts, patch('frontrow.server._stt_from_env') as stt:
                with self.assertRaisesRegex(RuntimeError, 'Policy demo requires'):
                    create_app()
                factory.assert_not_called()
                tts.assert_not_called()
                stt.assert_not_called()

    def test_default_off_keeps_coordination_disabled(self):
        with patch.dict(os.environ, {**ENV, 'FRONTROW_POLICY_COORDINATION': 'off'}):
            with TestClient(create_app()) as client:
                status = client.get('/policy/coordination/status').json()
                self.assertFalse(status['enabled'])
                exercise = client.post('/policy/exercises', json={'scenario_id': 'caption-failure'}).json()['exercise_id']
                self.assertEqual(client.post(f'/policy/exercises/{exercise}/coordinate',
                                             json={'expected_stage': 1}).status_code, 503)


if __name__ == '__main__':
    unittest.main()
