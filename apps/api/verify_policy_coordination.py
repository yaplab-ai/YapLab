"""Offline multi-role coordination protocol checks. No provider calls."""
from __future__ import annotations

import asyncio
import hashlib
import json
import unittest

from frontrow.llm.base import LLMClient
from frontrow.llm.fake import FakeLLM
from frontrow.llm.fallback import FallbackLLM
from frontrow.llm.openai_client import OpenAIClient
from frontrow.policy.coordination import coordinate, prepare_role_requests
from frontrow.policy.evidence import load_corpus
from frontrow.policy.scenarios import ExerciseStore


def snapshot(scenario='caption-failure', stage=2):
    store = ExerciseStore()
    created = store.create(scenario, 'teacher')
    exercise = created['exercise_id']
    for current in range(1, stage):
        store.advance(exercise, 'teacher', current)
    return {'scenario_id': scenario, 'stage': stage, 'role_views': {
        role: [fact for item in store.view(exercise, role)['released_stages'] for fact in item['facts']]
        for role in ('teacher', 'privacy', 'accessibility')}}


class Scripted(LLMClient):
    def __init__(self, overrides=None, delay=0):
        self.requests = []
        self.overrides = overrides or {}
        self.delay = delay
        self.active = 0
        self.peak = 0

    async def complete(self, system, user, *, model, timeout):
        payload = json.loads(user)
        self.requests.append((system, payload))
        self.active += 1
        self.peak = max(self.peak, self.active)
        try:
            if self.delay:
                await asyncio.sleep(self.delay)
            role = payload['role']
            if isinstance(self.overrides.get(role), Exception):
                raise self.overrides[role]
            actions = {'teacher': 'resume_vendor_workshop', 'privacy': 'verify_vendor_terms',
                       'accessibility': 'confirm_accessible_option'}
            action = actions[role] if actions[role] in payload['actions'] else next(iter(payload['actions']))
            output = {'proposals': [{'action_id': action, 'fact_ids': [payload['facts'][0]['id']],
                                     'source_ids': [payload['sources'][0]['id']]}], 'questions': []}
            override = self.overrides.get(role)
            if callable(override):
                output = override(output, payload)
            return json.dumps(output)
        finally:
            self.active -= 1


class CoordinationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.corpus = load_corpus()

    def test_preparation_scopes_and_stage_isolation(self):
        early = snapshot('transcript-disclosure', 1)
        late = snapshot('transcript-disclosure', 2)
        requests = prepare_role_requests(self.corpus, early)
        self.assertEqual(len(requests), 3)
        for request in requests:
            payload = json.loads(request['user'])
            role = request['role']
            self.assertEqual(payload['role'], role)
            self.assertEqual({x['id'] for x in payload['facts']}, {x['id'] for x in early['role_views'][role]})
            self.assertTrue(all('-1' in fact['id'] for fact in payload['facts']))
            self.assertNotIn('td-2c', request['user'])
            self.assertNotIn('uaeu-student-generative-ai', request['source_ids'])
        teacher = next(r for r in requests if r['role'] == 'teacher')
        access = next(r for r in requests if r['role'] == 'accessibility')
        self.assertNotIn('td-1c', teacher['user'])
        self.assertNotIn('td-1b', access['user'])
        privacy_late = next(r for r in prepare_role_requests(self.corpus, late) if r['role'] == 'privacy')
        self.assertIn('td-2c', privacy_late['user'])
        early['role_views']['privacy'][0]['text'] = 'changed after preparation'
        self.assertNotIn('changed after preparation', requests[1]['user'])
        in_scope = prepare_role_requests(self.corpus, snapshot(), institution='uaeu')
        self.assertTrue(all(json.loads(r['user'])['institution'] == 'uaeu' for r in in_scope))

    def test_three_role_calls_and_conditional_handoffs(self):
        async def run():
            fake = Scripted(delay=.01)
            result = await coordinate(self.corpus, snapshot(), fake, 'scripted', mode='offline_test')
            self.assertEqual(len(fake.requests), 3)
            self.assertEqual({payload['role'] for _, payload in fake.requests}, {'teacher', 'privacy', 'accessibility'})
            self.assertLessEqual(fake.peak, 2)
            self.assertEqual(result['review_mode'], 'offline_test')
            self.assertTrue(all(role['status'] == 'completed' for role in result['roles']))
            by_action = {item['action_id']: item for item in result['plan']}
            resumed = by_action['resume_vendor_workshop']
            self.assertEqual(set(resumed['depends_on']), {'verify_vendor_terms', 'confirm_accessible_option'})
            self.assertEqual({x['owner'] for x in resumed['handoffs']}, {'privacy', 'accessibility'})
            self.assertEqual(resumed['status'], 'awaiting_human_confirmation')
            self.assertNotIn('executed', resumed['status'])
        asyncio.run(run())

    def test_result_pins_exact_role_evidence_and_prompts(self):
        def digest(obj):
            return hashlib.sha256(json.dumps(obj, ensure_ascii=False, sort_keys=True,
                                             separators=(',', ':')).encode('utf-8')).hexdigest()
        async def run():
            state = snapshot()
            prepared = {item['role']: item for item in prepare_role_requests(self.corpus, state)}
            client = Scripted({'privacy': RuntimeError('provider-failed')})
            result = await coordinate(self.corpus, state, client, 'offline-model', mode='offline_test')
            self.assertEqual(result['protocol_version'], '1')
            self.assertEqual(result['corpus_version'], self.corpus.version)
            self.assertEqual(result['model'], {'provider': 'offline_test', 'model': 'offline-model'})
            actual = {payload['role']: (system, payload) for system, payload in client.requests}
            for role in result['roles']:
                request = prepared[role['role']]
                system, sent = actual[role['role']]
                self.assertEqual(sent['corpus_version'], self.corpus.version)
                self.assertEqual(sent['protocol_version'], '1')
                self.assertTrue(role['prompt_attempted'])
                self.assertEqual(role['prompt_sha256'], digest({'system': system, 'user': request['user']}))
                self.assertEqual(len(role['evidence']), len(sent['sources']))
                for evidence, source in zip(role['evidence'], sent['sources']):
                    copy = dict(evidence)
                    hashed = copy.pop('sha256')
                    self.assertEqual(copy, source)
                    self.assertEqual(hashed, digest(source))
                self.assertNotIn('user', role)
                self.assertNotIn('system', role)
            self.assertEqual(next(role for role in result['roles'] if role['role'] == 'privacy')['status'], 'unavailable')
            self.assertLess(len(json.dumps(result, ensure_ascii=False).encode('utf-8')), 65536)

            target = prepared['teacher']['source_ids'][0]
            changed_entries = [source.model_copy(update={'summary': source.summary + ' Revised note.'})
                               if source.id == target else source for source in self.corpus.entries]
            updated = self.corpus.model_copy(update={'version': 'updated-test-version', 'entries': changed_entries})
            revised = await coordinate(updated, state, Scripted(), 'offline-model')
            original_teacher = next(role for role in result['roles'] if role['role'] == 'teacher')
            revised_teacher = next(role for role in revised['roles'] if role['role'] == 'teacher')
            self.assertEqual(revised['corpus_version'], 'updated-test-version')
            self.assertNotEqual(original_teacher['prompt_sha256'], revised_teacher['prompt_sha256'])
            before = next(item for item in original_teacher['evidence'] if item['id'] == target)
            after = next(item for item in revised_teacher['evidence'] if item['id'] == target)
            self.assertNotEqual(before['sha256'], after['sha256'])
        asyncio.run(run())

    def test_unavailable_role_and_missing_dependency(self):
        async def run():
            result = await coordinate(self.corpus, snapshot(), Scripted({'privacy': RuntimeError('secret')}), 'test')
            privacy = next(role for role in result['roles'] if role['role'] == 'privacy')
            self.assertEqual(privacy['status'], 'unavailable')
            self.assertEqual(privacy['reason'], 'provider_error')
            self.assertNotIn('secret', str(result))
            resume = next(item for item in result['plan'] if item['action_id'] == 'resume_vendor_workshop')
            self.assertEqual(resume['status'], 'missing_prerequisites')
            self.assertTrue(any('verify_vendor_terms' in gap for gap in result['unresolved']))
        asyncio.run(run())

    def test_invalid_fact_source_action_question_and_institution(self):
        def bad_action(out, payload):
            out['proposals'][0]['action_id'] = 'do_something_unapproved'
            return out
        def other_role_fact(out, payload):
            out['proposals'][0]['fact_ids'] = ['cf-2c']  # accessibility only
            return out
        def invented_source(out, payload):
            out['proposals'][0]['source_ids'] = ['invented-source']
            return out
        def excluded_source(out, payload):
            out['proposals'][0]['source_ids'] = ['uaeu-student-generative-ai']
            return out
        def bad_question(out, payload):
            out['questions'] = ['hidden_question']
            return out
        async def run():
            for change in (bad_action, other_role_fact, invented_source, excluded_source, bad_question):
                result = await coordinate(self.corpus, snapshot(), Scripted({'teacher': change}), 'test')
                teacher = next(role for role in result['roles'] if role['role'] == 'teacher')
                self.assertEqual(teacher['status'], 'unavailable')
                self.assertEqual(teacher['reason'], 'invalid_response')
                self.assertEqual(teacher['proposals'], [])
                self.assertNotIn('do_something_unapproved', str(result))
        asyncio.run(run())

    def test_conflicting_proposals_are_unresolved(self):
        def conflict(out, payload):
            original = out['proposals'][0]
            out['proposals'] = [dict(original, action_id='delay_workshop'), dict(original, action_id='start_workshop_now')]
            return out
        async def run():
            result = await coordinate(self.corpus, snapshot(), Scripted({'teacher': conflict}), 'test')
            self.assertTrue(any('Conflicting' in text for text in result['unresolved']))
            teacher = [item for item in result['plan'] if item['owner'] == 'teacher']
            self.assertEqual({x['status'] for x in teacher}, {'conflicting_proposals'})
        asyncio.run(run())

    def test_empty_role_proposal_requires_human_review(self):
        def empty(out, payload):
            return {'proposals': [], 'questions': []}
        async def run():
            result = await coordinate(self.corpus, snapshot(), Scripted({'privacy': empty}), 'test')
            self.assertTrue(any('privacy role proposed no action' in item for item in result['unresolved']))
            self.assertTrue(any('verify_vendor_terms' in item for item in result['unresolved']))
        asyncio.run(run())

    def test_stage_gates_and_every_scenario(self):
        for scenario in ('transcript-disclosure', 'caption-failure', 'feedback-as-grade'):
            first = prepare_role_requests(self.corpus, snapshot(scenario, 1))
            second = prepare_role_requests(self.corpus, snapshot(scenario, 2))
            for early, late in zip(first, second):
                self.assertTrue(set(early['action_ids']) <= set(late['action_ids']))
                self.assertTrue(set(early['fact_ids']) <= set(late['fact_ids']))
                self.assertTrue(set(early['source_ids']))
            self.assertTrue(any(set(late['action_ids']) - set(early['action_ids']) for early, late in zip(first, second)))

    def test_role_and_overall_timeouts_and_cancellation(self):
        async def run():
            fake = Scripted(delay=.2)
            role_timeout = await coordinate(self.corpus, snapshot(), fake, 'test', role_timeout=.01)
            self.assertTrue(all(role['status'] == 'unavailable' and role['reason'] == 'timeout' for role in role_timeout['roles']))
            self.assertEqual(fake.active, 0)
            fake = Scripted(delay=.2)
            overall = await coordinate(self.corpus, snapshot(), fake, 'test', total_timeout=.01)
            self.assertTrue(all(role['reason'] == 'overall_timeout' for role in overall['roles']))
            self.assertEqual([role['prompt_attempted'] for role in overall['roles']], [True, True, False])
            self.assertTrue(all(role['evidence'] and len(role['prompt_sha256']) == 64 for role in overall['roles']))
            self.assertEqual(fake.active, 0)
            fake = Scripted(delay=1)
            task = asyncio.create_task(coordinate(self.corpus, snapshot(), fake, 'test'))
            while fake.active < 2:
                await asyncio.sleep(.001)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
            self.assertEqual(fake.active, 0)
        asyncio.run(run())

    def test_provider_metadata_with_mock_adapter(self):
        class MockDirectProvider(OpenAIClient):
            def __init__(self):
                self.provider_name = 'nebius'
                self.scripted = Scripted()
            async def complete(self, system, user, *, model, timeout):
                return await self.scripted.complete(system, user, model=model, timeout=timeout)
        async def run():
            mock = MockDirectProvider()
            result = await coordinate(self.corpus, snapshot(), mock, 'test-model', mode='model_assisted')
            self.assertEqual(result['model'], {'provider': 'nebius', 'model': 'test-model'})
            self.assertEqual(result['review_mode'], 'model_assisted')
            self.assertEqual(len(mock.scripted.requests), 3)
            mock.provider_name = 'unknown'
            with self.assertRaises(ValueError):
                await coordinate(self.corpus, snapshot(), mock, 'test-model', mode='model_assisted')
        asyncio.run(run())

    def test_mode_guards_prevent_fake_live_or_network_offline(self):
        async def run():
            with self.assertRaises(ValueError):
                await coordinate(self.corpus, snapshot(), FakeLLM(), 'test', mode='model_assisted')
            with self.assertRaises(ValueError):
                await coordinate(self.corpus, snapshot(), FallbackLLM(Scripted()), 'test', mode='model_assisted')
            with self.assertRaises(ValueError):
                await coordinate(self.corpus, snapshot(), Scripted(), 'test', mode='model_assisted')
            # Construct without SDK/network initialization to exercise the guard.
            direct_provider = object.__new__(OpenAIClient)
            with self.assertRaises(ValueError):
                await coordinate(self.corpus, snapshot(), direct_provider, 'test', mode='offline_test')
        asyncio.run(run())


if __name__ == '__main__':
    unittest.main()
