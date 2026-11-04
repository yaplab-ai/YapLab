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

    def test_atomic_checkpoint_preserves_prior_json_on_precommit_failure(self):
        dest = self.base / 'result.json'
        evaluation.reserve_output(dest)
        evaluation.atomic_checkpoint(dest, {'version': 1})
        old = dest.read_bytes()
        original_fdopen = evaluation.os.fdopen
        class FailedWriter:
            def __init__(self, fd, *args, **kwargs): self.stream = original_fdopen(fd, *args, **kwargs)
            def __enter__(self): return self
            def __exit__(self, *args): self.stream.close()
            def write(self, value): raise OSError('injected write failure')
        injections = [patch.object(evaluation.json, 'dump', side_effect=OSError('dump failed')),
                      patch.object(evaluation.os, 'fdopen', side_effect=FailedWriter),
                      patch.object(evaluation.os, 'fsync', side_effect=OSError('fsync failed')),
                      patch.object(evaluation.os, 'replace', side_effect=OSError('replace failed'))]
        for failure in injections:
            with self.subTest(failure=failure), failure, self.assertRaises(OSError):
                evaluation.atomic_checkpoint(dest, {'version': 2})
            self.assertEqual(dest.read_bytes(), old)
            self.assertEqual(json.loads(dest.read_text()), {'version': 1})
            self.assertEqual(list(self.base.iterdir()), [dest])
        evaluation.atomic_checkpoint(dest, {'version': 2})
        self.assertEqual(json.loads(dest.read_text()), {'version': 2})

    def test_directory_sync_failure_reports_uncertain_durability(self):
        dest = self.base / 'result.json'
        evaluation.reserve_output(dest)
        evaluation.atomic_checkpoint(dest, {'version': 1})
        actual_fsync = evaluation.os.fsync
        count = 0
        def fail_directory(fd):
            nonlocal count
            count += 1
            if count == 2:
                raise OSError('directory sync failed')
            return actual_fsync(fd)
        with patch.object(evaluation.os, 'fsync', side_effect=fail_directory), self.assertRaises(OSError):
            evaluation.atomic_checkpoint(dest, {'version': 2})
        # Replacement happened, but it is not safe to claim directory durability.
        self.assertEqual(json.loads(dest.read_text()), {'version': 2})
        self.assertEqual(list(self.base.iterdir()), [dest])

    def test_reservation_rejects_existing_file_and_symlink_paths(self):
        existing = self.base / 'existing'
        existing.write_text('preserve')
        with self.assertRaises(FileExistsError):
            evaluation.reserve_output(existing)
        link = self.base / 'alias'
        link.symlink_to(existing)
        with self.assertRaises(ValueError):
            evaluation.reserve_output(link)
        parent_link = self.base / 'linked-dir'
        parent_link.symlink_to(self.base, target_is_directory=True)
        with self.assertRaises(ValueError):
            evaluation.reserve_output(parent_link / 'new')
        self.assertEqual(existing.read_text(), 'preserve')
        self.assertFalse((self.base / 'new').exists())

    def test_live_exit_status_distinguishes_stopped_and_structural_failure(self):
        for index, (status, validation, expected) in enumerate((('completed', 'pass', 0),
                                      ('completed', 'fail', 2), ('stopped', 'not_complete', 1))):
            async def stub(corpus, states, plan, approval, *, checkpoint):
                result = {'run_status': status, 'structural_validation': validation}
                checkpoint(result)
                return result
            output = self.base / f'{index}.json'
            stream = io.StringIO()
            with self.subTest(status=status, validation=validation), \
                 patch.dict(evaluation.os.environ, {'NEBIUS_API_KEY': 'test-only'}), \
                 patch.object(evaluation.importlib.util, 'find_spec', return_value=object()), \
                 patch.object(evaluation, 'run_live', side_effect=stub), \
                 patch.object(sys, 'argv', ['evaluate_coordination.py', '--execute-live', '--provider', 'nebius',
                                           '--approval-reference', 'approved', '--output', str(output)]), \
                 redirect_stdout(stream):
                self.assertEqual(evaluation.main(), expected)
            self.assertIn('run_status=' + status, stream.getvalue())
            self.assertIn('structural_validation=' + validation, stream.getvalue())
            self.assertEqual(json.loads(output.read_text())['run_status'], status)

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
        self.assertEqual(result['structural_validation'], 'not_complete')
        self.assertEqual(result['snapshots'][0]['structural_validation'], 'fail')
        self.assertTrue(all(r['reason'] == 'invalid_response' for r in result['snapshots'][0]['roles']))
        self.assertEqual(result['validation_issue_counts'], {'unknown_action_id': 3})
        self.assertEqual(result['human_semantic_quality'], 'unreviewed')

    def test_usage_fields_are_bounded_and_allowlisted(self):
        item = evaluation.bounded_usage({'kind': 'request', 'role': 'leak-secret', 'outcome': 'leak-secret',
            'usage': {'prompt_tokens': True, 'completion_tokens': 1_000_000_001}, 'secret': 'private'})
        self.assertEqual(item, {'scenario_id': None, 'stage': None, 'role': None, 'outcome': 'unknown',
                                'finish_reason': None, 'error_type': None, 'latency_ms': None,
                                'input_tokens': None, 'output_tokens': None})
        self.assertIsNone(evaluation.bounded_usage({'kind': 'fallback'}))
        self.assertIsNone(evaluation.bounded_usage({'kind': 'request', 'usage': 'bad'})['input_tokens'])
        known = evaluation.bounded_usage({'kind': 'request', 'role': 'policy_coordination_teacher',
            'finish_reason': 'length', 'error_type': 'APITimeoutError', 'latency_seconds': 1.2345},
            scenario_id='caption-failure', stage=2)
        self.assertEqual((known['finish_reason'], known['error_type'], known['latency_ms']), ('length', 'APITimeoutError', 1234.5))
        self.assertEqual((known['scenario_id'], known['stage']), ('caption-failure', 2))
        self.assertIsNone(evaluation.bounded_usage({'kind': 'request', 'latency_seconds': 10**500})['latency_ms'])

    def test_unknown_validation_categories_are_dropped(self):
        corpus, states, _ = evaluation.prepare()
        class Invalid(OpenAIClient):
            provider_name = 'nebius'
            def __init__(self): self.attempts = 0
            async def aclose(self): pass
            async def complete(self, system, user, *, model, timeout):
                self.attempts += 1
                return '{"proposals": [], "questions": []}'
        from frontrow.policy.coordination import coordinate
        result = asyncio.run(coordinate(corpus, states[0], Invalid(), evaluation.MODEL, mode='model_assisted'))
        result['roles'][0].update(status='unavailable', reason='invalid_response', validation_issue='PRIVATE OUTPUT')
        result['roles'][1].update(status='unavailable', reason='invalid_response', validation_issue='json_syntax')
        result['roles'][2].update(status='unavailable', reason='provider_error', validation_issue='json_syntax')
        sanitized = evaluation.summarize(result)
        self.assertNotIn('validation_issue', sanitized['roles'][0])
        self.assertEqual(sanitized['roles'][1]['validation_issue'], 'json_syntax')
        self.assertNotIn('validation_issue', sanitized['roles'][2])
        self.assertNotIn('PRIVATE OUTPUT', json.dumps(sanitized))
        progress = evaluation.evaluation_progress(corpus, {'pricing': {}}, 'ok', Invalid(), [sanitized], [], status='stopped')
        self.assertEqual(progress['validation_issue_counts'], {'json_syntax': 1})
        self.assertEqual(progress['invalid_response_without_known_issue'], 1)

    def test_optional_source_metadata_preserved_only_when_present(self):
        corpus, states, _ = evaluation.prepare()
        class Valid(OpenAIClient):
            provider_name = 'nebius'
            def __init__(self): self.attempts = 0
            async def aclose(self): pass
            async def complete(self, system, user, *, model, timeout):
                self.attempts += 1
                return '{"proposals": [], "questions": []}'
        from frontrow.policy.coordination import coordinate
        result = asyncio.run(coordinate(corpus, states[0], Valid(), evaluation.MODEL, mode='model_assisted'))
        evidence = result['roles'][0]['evidence'][0]
        evidence['source_locator'] = 'Section 2'
        evidence['verification'] = 'Public primary source checked'
        evidence['sha256'] = digest({k: v for k, v in evidence.items() if k != 'sha256'})
        expected_hash = evidence['sha256']
        evidence['private_unknown_key'] = 'PRIVATE OUTPUT'
        historical = result['roles'][1]['evidence'][0]
        historical.pop('source_locator', None)
        historical.pop('verification', None)
        summarized = evaluation.summarize(result)
        observed = summarized['roles'][0]['evidence'][0]
        self.assertEqual(observed['source_locator'], 'Section 2')
        self.assertEqual(observed['verification'], 'Public primary source checked')
        self.assertEqual(observed['sha256'], expected_hash)
        self.assertNotIn('private_unknown_key', observed)
        self.assertNotIn('PRIVATE OUTPUT', json.dumps(summarized))
        historical_result = summarized['roles'][1]['evidence'][0]
        self.assertNotIn('source_locator', historical_result)
        self.assertNotIn('verification', historical_result)

    def test_partial_status_preserves_valid_items_but_fails_structural_check(self):
        corpus, states, plan = evaluation.prepare()
        class Valid(OpenAIClient):
            provider_name = 'nebius'
            def __init__(self): self.attempts = 0
            async def aclose(self): pass
            async def complete(self, system, user, *, model, timeout):
                self.attempts += 1
                payload = json.loads(user)
                return json.dumps({'proposals': [{'action_id': next(iter(payload['actions'])),
                    'fact_ids': [payload['facts'][0]['id']], 'source_ids': [payload['sources'][0]['id']]}],
                    'questions': [next(iter(payload['questions']))]})
        from frontrow.policy.coordination import coordinate
        client = Valid()
        result = asyncio.run(coordinate(corpus, states[0], client, evaluation.MODEL, mode='model_assisted'))
        result['roles'][0].update(status='partial', reason='invalid_response', validation_issue='unknown_action_id')
        result['roles'][1].update(status='unknown private value', reason='invalid_response', validation_issue='PRIVATE OUTPUT')
        summarized = evaluation.summarize(result)
        partial = summarized['roles'][0]
        self.assertEqual(partial['status'], 'partial')
        self.assertEqual(partial['validation_issue'], 'unknown_action_id')
        self.assertEqual(partial['proposals'], [{k: result['roles'][0]['proposals'][0][k]
                                                 for k in ('action_id', 'fact_ids', 'source_ids')}])
        self.assertEqual(partial['question_ids'], [result['roles'][0]['questions'][0]['question_id']])
        self.assertEqual(summarized['roles'][1]['status'], 'unavailable')
        self.assertNotIn('validation_issue', summarized['roles'][1])
        self.assertNotIn('PRIVATE OUTPUT', json.dumps(summarized))
        self.assertNotIn('unknown private value', json.dumps(summarized))
        self.assertEqual(summarized['structural_validation'], 'fail')
        usage = [{'input_tokens': 11, 'output_tokens': 12, 'outcome': 'success'} for _ in range(3)]
        progress = evaluation.evaluation_progress(corpus, plan, 'approved', client, [summarized], usage, status='completed')
        self.assertEqual(progress['partially_completed_roles'], 1)
        self.assertEqual(progress['structurally_failed_roles'], 2)
        self.assertEqual(progress['validation_issue_counts'], {'unknown_action_id': 1})
        self.assertEqual(progress['structural_validation'], 'fail')
        self.assertEqual(progress['reported_usage_cost']['known_cost_usd'], 0.00001062)
        self.assertEqual(progress['human_semantic_quality'], 'unreviewed')

    def test_missing_usage_stops_future_snapshots(self):
        class Missing(OpenAIClient):
            provider_name = 'nebius'
            def __init__(self): self.attempts = 0
            async def aclose(self): pass
            async def complete(self, system, user, *, model, timeout):
                self.attempts += 1
                emit_llm_event('request', provider='nebius', model=model, latency_seconds=0,
                               usage=None, outcome='success')
                return '{"proposals": [], "questions": []}'
        corpus, states, plan = evaluation.prepare()
        with patch.object(evaluation, 'LimitedNebius', Missing), patch.object(llm_logger, 'info'):
            result = asyncio.run(evaluation.run_live(corpus, states, plan, 'approved'))
        self.assertEqual(result['run_status'], 'stopped')
        self.assertEqual(result['stop_reason'], 'usage_missing')
        self.assertEqual(result['completed_snapshots'], 1)
        self.assertEqual(result['provider_call_attempts'], 3)
        self.assertEqual(result['usage_missing_calls'], 3)
        self.assertIsNone(result['reported_usage_cost']['complete_cost_usd'])

    def test_reported_output_over_limit_stops_next_snapshot(self):
        class OverLimit(OpenAIClient):
            provider_name = 'nebius'
            def __init__(self): self.attempts = 0
            async def aclose(self): pass
            async def complete(self, system, user, *, model, timeout):
                self.attempts += 1
                emit_llm_event('request', provider='nebius', model=model, latency_seconds=0,
                               usage={'prompt_tokens': 10, 'completion_tokens': 401}, outcome='success')
                return '{"proposals": [], "questions": []}'
        corpus, states, plan = evaluation.prepare()
        with patch.object(evaluation, 'LimitedNebius', OverLimit), patch.object(llm_logger, 'info'):
            result = asyncio.run(evaluation.run_live(corpus, states, plan, 'approved'))
        self.assertEqual(result['stop_reason'], 'reported_output_limit_exceeded')
        self.assertEqual(result['provider_call_attempts'], 3)
        self.assertEqual(result['completed_snapshots'], 1)
        self.assertIsNone(result['reported_usage_cost']['complete_cost_usd'])

    def test_reported_cost_at_budget_stops_next_snapshot(self):
        class AtBudget(OpenAIClient):
            provider_name = 'nebius'
            def __init__(self): self.attempts = 0
            async def aclose(self): pass
            async def complete(self, system, user, *, model, timeout):
                self.attempts += 1
                emit_llm_event('request', provider='nebius', model=model, latency_seconds=0,
                               usage={'prompt_tokens': 500000, 'completion_tokens': 0}, outcome='success')
                return '{"proposals": [], "questions": []}'
        corpus, states, plan = evaluation.prepare()
        plan['pricing']['planned_budget_usd'] = 0.09
        with patch.object(evaluation, 'LimitedNebius', AtBudget), patch.object(llm_logger, 'info'):
            result = asyncio.run(evaluation.run_live(corpus, states, plan, 'approved'))
        self.assertEqual(result['stop_reason'], 'reported_cost_budget_reached')
        self.assertEqual(result['provider_call_attempts'], 3)
        self.assertEqual(result['reported_usage_cost']['known_cost_usd'], 0.09)
        self.assertFalse(result['reported_usage_cost']['invoice_verified'])

    def test_reported_usage_cost_uses_plan_prices_and_partial_usage(self):
        _, _, plan = evaluation.prepare()
        plan['pricing']['input_per_million'] = 0.12
        plan['pricing']['output_per_million'] = 0.48
        records = [{'input_tokens': 1000000, 'output_tokens': None},
                   {'input_tokens': None, 'output_tokens': 500000}]
        self.assertEqual(str(evaluation.known_usage_cost(records, plan)), '0.36')

    def test_provider_failure_stops_and_redacts_exception(self):
        class Failed(OpenAIClient):
            provider_name = 'nebius'
            def __init__(self): self.attempts = 0
            async def aclose(self): pass
            async def complete(self, system, user, *, model, timeout):
                self.attempts += 1
                emit_llm_event('request', provider='nebius', model=model, latency_seconds=0,
                               usage=None, outcome='error', error_type='SensitiveException')
                raise RuntimeError('private response text')
        corpus, states, plan = evaluation.prepare()
        with patch.object(evaluation, 'LimitedNebius', Failed), patch.object(llm_logger, 'info'):
            result = asyncio.run(evaluation.run_live(corpus, states, plan, 'approved'))
        self.assertEqual(result['stop_reason'], 'provider_or_internal_failure')
        self.assertEqual(result['provider_call_attempts'], 3)
        self.assertEqual(result['provider_failure_events'], 3)
        self.assertNotIn('private response text', json.dumps(result))
        self.assertNotIn('SensitiveException', json.dumps(result))

    def test_checkpoint_failure_stops_and_retains_usage_in_recovery_output(self):
        class Good(OpenAIClient):
            provider_name = 'nebius'
            def __init__(self): self.attempts = 0
            async def aclose(self): pass
            async def complete(self, system, user, *, model, timeout):
                self.attempts += 1
                emit_llm_event('request', provider='nebius', model=model, latency_seconds=0,
                               usage={'prompt_tokens': 10, 'completion_tokens': 20}, outcome='success')
                return '{"proposals": [], "questions": []}'
        corpus, states, plan = evaluation.prepare()
        checkpoints = []
        def checkpoint(value):
            checkpoints.append(value)
            if value['completed_snapshots']:
                raise OSError('private exception')
        stderr = io.StringIO()
        with patch.object(evaluation, 'LimitedNebius', Good), patch.object(llm_logger, 'info'), redirect_stderr(stderr):
            with self.assertRaises(evaluation.CheckpointFailure):
                asyncio.run(evaluation.run_live(corpus, states, plan, 'approved', checkpoint=checkpoint))
        self.assertEqual(checkpoints[-1]['provider_call_attempts'], 3)
        self.assertEqual(checkpoints[-1]['usage_missing_calls'], 0)
        recovery = json.loads(stderr.getvalue().splitlines()[-1])
        self.assertEqual(recovery['stop_reason'], 'checkpoint_failed')
        self.assertEqual(len(recovery['usage']), 3)
        self.assertEqual(recovery['usage'][0]['input_tokens'], 10)
        self.assertNotIn('private exception', stderr.getvalue())

    def test_atomic_checkpoint_failure_stops_run_preserves_prior_file_and_usage(self):
        class Good(OpenAIClient):
            provider_name = 'nebius'
            def __init__(self): self.attempts = 0
            async def aclose(self): pass
            async def complete(self, system, user, *, model, timeout):
                self.attempts += 1
                emit_llm_event('request', provider='nebius', model=model, latency_seconds=0,
                               usage={'prompt_tokens': 10, 'completion_tokens': 20}, outcome='success')
                return '{"proposals": [], "questions": []}'
        corpus, states, plan = evaluation.prepare()
        dest = self.base / 'run.json'
        evaluation.reserve_output(dest)
        actual_replace = evaluation.os.replace
        count = 0
        def replace_before_failure(src, dst):
            nonlocal count
            count += 1
            if count == 3:
                raise OSError('injected failure')
            return actual_replace(src, dst)
        stderr = io.StringIO()
        with patch.object(evaluation, 'LimitedNebius', Good), patch.object(llm_logger, 'info'), \
             patch.object(evaluation.os, 'replace', side_effect=replace_before_failure), redirect_stderr(stderr):
            with self.assertRaises(evaluation.CheckpointFailure):
                asyncio.run(evaluation.run_live(corpus, states, plan, 'approved',
                            checkpoint=lambda value: evaluation.atomic_checkpoint(dest, value)))
        previous = json.loads(dest.read_text())
        self.assertEqual(previous['run_status'], 'in_progress')
        self.assertIsNotNone(previous['in_flight_snapshot'])
        self.assertEqual(previous['provider_call_attempts'], 0)
        recovery = json.loads(stderr.getvalue().splitlines()[-1])
        self.assertEqual(recovery['provider_call_attempts'], 3)
        self.assertEqual(recovery['stop_reason'], 'checkpoint_failed')
        self.assertEqual(len(recovery['usage']), 3)
        self.assertEqual(list(self.base.iterdir()), [dest])

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
        self.assertEqual(result['run_status'], 'completed')
        self.assertEqual((result['completed_snapshots'], result['structurally_completed_roles']), (9, 27))
        self.assertEqual(result['reported_usage_cost']['known_cost_usd'], 0.00009558)
        self.assertFalse(result['reported_usage_cost']['invoice_verified'])
        self.assertEqual(len(result['usage']), 27)
        self.assertTrue(all(u['scenario_id'] in evaluation.SCENARIOS and u['stage'] in (1, 2, 3) for u in result['usage']))
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
