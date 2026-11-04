"""Offline verification: .venv/bin/python verify_policy_evaluation.py"""
from __future__ import annotations

import asyncio
import hashlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from types import SimpleNamespace

from frontrow.llm.base import emit_llm_event, llm_logger
from frontrow.llm.openai_client import OpenAIClient

spec = importlib.util.spec_from_file_location('coord_eval', Path(__file__).parent / 'scripts' / 'evaluate_coordination.py')
evaluation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evaluation)


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':')).encode('utf-8')).hexdigest()


class NoEnvironment:
    def get(self, *args, **kwargs):
        raise AssertionError('default dry-run read the environment')
    def __getitem__(self, key):
        raise AssertionError('default dry-run read the environment')
    def __contains__(self, key):
        raise AssertionError('default dry-run read the environment')


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(tempfile.gettempdir()).resolve())
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)

    def invoke(self, args):
        with patch.object(sys, 'argv', ['evaluate_coordination.py', *args]), redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            return evaluation.main()

    def test_default_dry_run_is_network_free_and_never_reads_environment(self):
        with patch('socket.socket', side_effect=AssertionError('network forbidden')), \
             patch.object(OpenAIClient, '__init__', side_effect=AssertionError('provider construction forbidden')):
            with patch.object(evaluation.os, 'environ', NoEnvironment()):
                corpus, states, plan = evaluation.prepare()
            self.assertEqual(self.invoke([]), 0)
        self.assertEqual(len(states), 9)
        self.assertEqual(plan['planned_provider_calls'], 27)
        self.assertEqual(plan['network_calls_made'], 0)
        self.assertEqual(len({(c['scenario_id'], c['stage'], c['role']) for c in plan['calls']}), 27)
        self.assertEqual(plan['corpus_version'], corpus.version)
        self.assertEqual(plan['prompt_utf8_bytes_total'], sum(c['input_utf8_bytes'] for c in plan['calls']))
        for state in states:
            calls = [c for c in plan['calls'] if (c['scenario_id'], c['stage']) == (state['scenario_id'], state['stage'])]
            for request in evaluation.prepare_role_requests(corpus, state, 'general'):
                call = next(c for c in calls if c['role'] == request['role'])
                self.assertEqual(call['input_utf8_bytes'], len(request['system'].encode()) + len(request['user'].encode()))
                self.assertEqual(call['prompt_sha256'], digest({'system': request['system'], 'user': request['user']}))
                self.assertFalse(call['prompt_attempted'])
                for evidence in call['evidence']:
                    self.assertEqual(evidence['sha256'], digest({k: v for k, v in evidence.items() if k != 'sha256'}))

    def test_live_gate_and_exclusive_output(self):
        for args in (['--execute-live'], ['--execute-live', '--provider', 'nebius'],
                     ['--execute-live', '--provider', 'nebius', '--approval-reference', 'approved'],
                     ['--model', 'unsupported'], ['--approval-reference', 'approved']):
            with self.subTest(args=args), patch.object(OpenAIClient, '__init__', side_effect=AssertionError('network client constructed')):
                with self.assertRaises(SystemExit) as exc:
                    self.invoke(args)
                self.assertEqual(exc.exception.code, 2)
        target = self.base / 'existing.json'
        target.write_text('preserve')
        with patch.object(OpenAIClient, '__init__', side_effect=AssertionError('network client constructed')):
            with self.assertRaises(SystemExit):
                self.invoke(['--output', str(target)])
        self.assertEqual(target.read_text(), 'preserve')
        with patch.dict(evaluation.os.environ, {'NEBIUS_API_KEY': 'test-only'}), \
             patch.object(evaluation.importlib.util, 'find_spec', return_value=object()), \
             patch.object(evaluation, 'run_live', side_effect=AssertionError('network run started')):
            with self.assertRaises(SystemExit):
                self.invoke(['--execute-live', '--provider', 'nebius', '--approval-reference', 'approved', '--output', str(target)])
        self.assertEqual(target.read_text(), 'preserve')

    def test_call_cap_and_model_guard_before_provider(self):
        async def check():
            client = object.__new__(evaluation.LimitedNebius)
            client.provider_name = 'nebius'
            client.attempts = 0
            with patch.object(OpenAIClient, 'complete', new=AsyncMock(return_value='{}')) as upstream:
                with self.assertRaises(ValueError):
                    await client.complete('s', 'u', model='wrong', timeout=1)
                self.assertEqual(client.attempts, 0)
                for _ in range(27):
                    await client.complete('s', 'u', model=evaluation.MODEL, timeout=1)
                with self.assertRaises(ValueError):
                    await client.complete('s', 'u', model=evaluation.MODEL, timeout=1)
                self.assertEqual(upstream.await_count, 27)
        asyncio.run(check())

    def test_nebius_adapter_disables_retries_and_caps_output(self):
        async def check():
            response = SimpleNamespace(usage=None, choices=[SimpleNamespace(
                finish_reason='stop', message=SimpleNamespace(content='{}'))])
            create = AsyncMock(return_value=response)
            sdk = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)),
                                  close=AsyncMock())
            factory = MagicMock(return_value=sdk)
            with patch.dict(sys.modules, {'openai': SimpleNamespace(AsyncOpenAI=factory)}), patch.object(llm_logger, 'info'):
                client = OpenAIClient(api_key='test-only', provider='nebius')
                await client.complete('system', 'user', model=evaluation.MODEL, timeout=3)
                await client.aclose()
            self.assertEqual(factory.call_args.kwargs['max_retries'], 0)
            self.assertEqual(create.await_count, 1)
            self.assertEqual(create.await_args.kwargs['max_tokens'], 400)
            self.assertEqual(create.await_args.kwargs['extra_body'], {'chat_template_kwargs': {'enable_thinking': False}})
        asyncio.run(check())

    def test_invalid_role_responses_are_structural_failures(self):
        class Invalid(OpenAIClient):
            provider_name = 'nebius'
            def __init__(self): self.attempts = 0
            async def aclose(self): pass
            async def complete(self, system, user, *, model, timeout):
                self.attempts += 1
                return json.dumps({'proposals': [{'action_id': 'not-allowed', 'fact_ids': ['not-allowed'],
                                                  'source_ids': ['not-allowed']}], 'questions': []})
        corpus, states, plan = evaluation.prepare()
        with patch.object(evaluation, 'LimitedNebius', Invalid):
            result = asyncio.run(evaluation.run_live(corpus, states[:1], plan, 'approval-id'))
        self.assertEqual(result['structural_validation'], 'fail')
        self.assertTrue(all(r['reason'] == 'invalid_response' for r in result['snapshots'][0]['roles']))
        self.assertEqual(result['human_semantic_quality'], 'unreviewed')

    def test_usage_fields_are_bounded_and_allowlisted(self):
        item = evaluation.bounded_usage({'kind': 'request', 'role': 'leak-secret', 'outcome': 'leak-secret',
            'usage': {'prompt_tokens': True, 'completion_tokens': 1_000_000_001}, 'secret': 'private'})
        self.assertEqual(item, {'role': None, 'outcome': 'unknown', 'input_tokens': None, 'output_tokens': None})
        self.assertIsNone(evaluation.bounded_usage({'kind': 'fallback'}))
        self.assertIsNone(evaluation.bounded_usage({'kind': 'request', 'usage': 'bad'})['input_tokens'])

    def test_mock_run_preserves_provenance_and_validates_responses(self):
        class Stub(OpenAIClient):
            provider_name = 'nebius'
            def __init__(self): self.attempts = 0
            async def aclose(self): pass
            async def complete(self, system, user, *, model, timeout):
                self.attempts += 1
                payload = json.loads(user)
                emit_llm_event('request', provider='nebius', model=model, latency_seconds=0,
                               usage={'prompt_tokens': 11, 'completion_tokens': 12}, outcome='success')
                return json.dumps({'proposals': [{'action_id': next(iter(payload['actions'])),
                    'fact_ids': [payload['facts'][0]['id']], 'source_ids': [payload['sources'][0]['id']]}], 'questions': []})
        corpus, states, plan = evaluation.prepare()
        with patch.object(evaluation, 'LimitedNebius', Stub), patch.object(llm_logger, 'info'):
            result = asyncio.run(evaluation.run_live(corpus, states, plan, 'approval-id'))
        self.assertEqual(result['provider_call_attempts'], 27)
        self.assertEqual(result['usage_missing_calls'], 0)
        self.assertEqual(len(result['usage']), 27)
        self.assertEqual(result['structural_validation'], 'pass')
        self.assertEqual(result['human_semantic_quality'], 'unreviewed')
        self.assertEqual(result['model'], {'provider': 'nebius', 'model': evaluation.MODEL})
        for snapshot in result['snapshots']:
            self.assertEqual(snapshot['corpus_version'], corpus.version)
            self.assertEqual(snapshot['protocol_version'], plan['protocol_version'])
            self.assertEqual(snapshot['model'], result['model'])
            for role in snapshot['roles']:
                call = next(c for c in plan['calls'] if (c['scenario_id'], c['stage'], c['role']) ==
                            (snapshot['scenario_id'], snapshot['stage'], role['role']))
                self.assertEqual(role['prompt_sha256'], call['prompt_sha256'])
                self.assertTrue(role['prompt_attempted'])
                self.assertEqual(role['evidence'], call['evidence'])
                self.assertEqual(set(role['proposals'][0]), {'action_id', 'fact_ids', 'source_ids'})
        self.assertNotIn('"system"', json.dumps(result))
        self.assertNotIn('"user"', json.dumps(result))


if __name__ == '__main__':
    unittest.main()
