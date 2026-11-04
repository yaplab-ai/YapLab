"""Offline HTTP/lifecycle/budget checks; all provider responses are test doubles."""
from __future__ import annotations

import asyncio
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from frontrow.limits import LimitExceeded
from frontrow.llm.fallback import FallbackLLM
from frontrow.llm.fake import FakeLLM
from frontrow.llm.openai_client import OpenAIClient, PROVIDERS
from frontrow.policy.router import ModelCallLimits, create_router
from frontrow.policy.scenarios import router as scenario_router
from verify_policy_coordination import Scripted


def app_for(fake=None, review=None):
    app = FastAPI()
    app.include_router(create_router(llm=review, coordination_llm=fake,
        coordination_mode='offline_test', model='scripted'))
    app.include_router(scenario_router)
    return app


def create(client):
    return client.post('/policy/exercises', json={'scenario_id': 'caption-failure'}).json()['exercise_id']


class CoordinationAPITests(unittest.TestCase):
    def test_disabled_and_strict_request(self):
        with TestClient(app_for()) as client:
            response = client.get('/policy/coordination/status')
            self.assertEqual(response.json(), {'enabled': False, 'review_mode': 'offline_test'})
            self.assertEqual(response.headers['cache-control'], 'no-store')
            exercise = create(client)
            response = client.post(f'/policy/exercises/{exercise}/coordinate', json={'expected_stage': 1})
            self.assertEqual(response.status_code, 503)
            self.assertIsNone(client.app.state.policy_exercise_store.exercises[exercise]['coordination_pending'])
        fake = Scripted()
        with TestClient(app_for(fake)) as client:
            exercise = create(client)
            for body in ({'expected_stage': True}, {'expected_stage': 1, 'mode': 'model_assisted'},
                         {'expected_stage': 1, 'institution': 'other'}):
                self.assertEqual(client.post(f'/policy/exercises/{exercise}/coordinate', json=body).status_code, 422)
            self.assertEqual(client.post(f'/policy/exercises/{exercise}/coordinate', json={'expected_stage': 2}).status_code, 409)
            self.assertEqual(fake.requests, [])

    def test_round_retrieval_role_audit_and_duplicate(self):
        fake = Scripted()
        with TestClient(app_for(fake)) as client:
            exercise = create(client)
            response = client.post(f'/policy/exercises/{exercise}/coordinate', json={'expected_stage': 1})
            self.assertEqual(response.status_code, 200, response.text)
            result = response.json()
            self.assertEqual(result['review_mode'], 'offline_test')
            self.assertEqual(len(fake.requests), 3)
            saved = client.get(f"/policy/exercises/{exercise}/coordination/{result['round_id']}")
            self.assertEqual(saved.json(), result)
            for role in ('teacher', 'privacy', 'accessibility'):
                audit = client.get(f'/policy/exercises/{exercise}/audit', params={'role': role}).json()
                event = audit['events'][0]
                self.assertEqual(event['round_id'], result['round_id'])
                self.assertEqual(event['assessment']['role'], role)
                self.assertNotIn('plan', event)
                self.assertNotIn('roles', event)
                other_ids = {fact['id'] for _, payload in fake.requests if payload['role'] != role
                             for fact in payload['facts'] if fact['id'] not in {
                                 f['id'] for _, mine in fake.requests if mine['role'] == role for f in mine['facts']}}
                self.assertFalse(any(x in json.dumps(event) for x in other_ids))
            duplicate = client.post(f'/policy/exercises/{exercise}/coordinate', json={'expected_stage': 1})
            self.assertEqual(duplicate.status_code, 409)
            self.assertEqual(len(fake.requests), 3)

    def test_atomic_three_call_limits_and_rollback(self):
        budget = ModelCallLimits()
        for _ in range(6):
            budget.reserve('one')
        with self.assertRaises(LimitExceeded):
            budget.reserve('one', 3)
        budget.reserve('one', 2)  # failed bulk reservation refunded its partial slots
        with self.assertRaises(LimitExceeded):
            budget.reserve('one')
        with self.assertRaises(ValueError):
            budget.reserve('two', True)
        daily = ModelCallLimits()
        for n in range(33):
            daily.reserve(str(n), 3)
        with self.assertRaises(LimitExceeded):
            daily.reserve('last', 3)
        daily.reserve('last')  # still exactly one daily slot after atomic failure

    def test_three_attempt_budget_shared_across_exercises(self):
        fake = Scripted()
        app = app_for(fake)
        with TestClient(app) as client:
            for _ in range(2):
                exercise = create(client)
                self.assertEqual(client.post(f'/policy/exercises/{exercise}/coordinate', json={'expected_stage': 1}).status_code, 200)
            exercise = create(client)
            response = client.post(f'/policy/exercises/{exercise}/coordinate', json={'expected_stage': 1})
            self.assertEqual(response.status_code, 429)
            self.assertIn('retry-after', response.headers)
            self.assertEqual(len(fake.requests), 6)
            self.assertIsNone(app.state.policy_exercise_store.exercises[exercise]['coordination_pending'])

    def test_stale_round_is_discarded_and_releases_reservation(self):
        async def run():
            class Signalled(Scripted):
                def __init__(self):
                    super().__init__(delay=.03)
                    self.started = asyncio.Event()
                async def complete(self, *args, **kwargs):
                    self.started.set()
                    return await super().complete(*args, **kwargs)
            fake = Signalled()
            app = app_for(fake)
            async with AsyncClient(transport=ASGITransport(app), base_url='http://test') as client:
                exercise = (await client.post('/policy/exercises', json={'scenario_id': 'caption-failure'})).json()['exercise_id']
                task = asyncio.create_task(client.post(f'/policy/exercises/{exercise}/coordinate', json={'expected_stage': 1}))
                await asyncio.wait_for(fake.started.wait(), 1)
                advanced = await client.post(f'/policy/exercises/{exercise}/advance', json={'expected_stage': 1})
                self.assertEqual(advanced.status_code, 200)
                self.assertEqual((await task).status_code, 409)
                state = app.state.policy_exercise_store.exercises[exercise]
                self.assertIsNone(state['coordination_pending'])
                self.assertEqual(state['coordination_results'], {})
                self.assertEqual((await client.post(f'/policy/exercises/{exercise}/coordinate', json={'expected_stage': 2})).status_code, 200)
        asyncio.run(run())

    def test_cancelled_round_releases_pending_and_semaphore(self):
        async def run():
            class Signalled(Scripted):
                def __init__(self):
                    super().__init__(delay=5)
                    self.started = asyncio.Event()
                async def complete(self, *args, **kwargs):
                    self.started.set()
                    return await super().complete(*args, **kwargs)
            fake = Signalled()
            app = app_for(fake)
            async with AsyncClient(transport=ASGITransport(app), base_url='http://test') as client:
                exercise = (await client.post('/policy/exercises', json={'scenario_id': 'caption-failure'})).json()['exercise_id']
                task = asyncio.create_task(client.post(f'/policy/exercises/{exercise}/coordinate', json={'expected_stage': 1}))
                await asyncio.wait_for(fake.started.wait(), 1)
                task.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await task
                state = app.state.policy_exercise_store.exercises[exercise]
                self.assertIsNone(state['coordination_pending'])
                self.assertEqual(fake.active, 0)
                fake.delay = 0
                response = await client.post(f'/policy/exercises/{exercise}/coordinate', json={'expected_stage': 1})
                self.assertEqual(response.status_code, 200)
        asyncio.run(run())

    def test_reviews_share_call_budget_and_concurrency_slots(self):
        async def run():
            class Both(Scripted):
                async def complete(self, system, user, *, model, timeout):
                    payload = json.loads(user)
                    if 'role' in payload:
                        return await super().complete(system, user, model=model, timeout=timeout)
                    self.active += 1
                    self.peak = max(self.peak, self.active)
                    try:
                        await asyncio.sleep(.02)
                        choice = payload['candidates'][0]
                        return json.dumps({'selections': [{'topic': choice['topic'],
                            'source_id': choice['source']['id'],
                            'requirement_index': choice['eligible_requirement_index']}]})
                    finally:
                        self.active -= 1
            fake = Both(delay=.02)
            app = app_for(fake, review=fake)
            async with AsyncClient(transport=ASGITransport(app), base_url='http://test') as client:
                exercise = (await client.post('/policy/exercises', json={'scenario_id': 'caption-failure'})).json()['exercise_id']
                replies = await asyncio.gather(
                    client.post(f'/policy/exercises/{exercise}/coordinate', json={'expected_stage': 1}),
                    client.post('/policy/review', json={'text': 'privacy personal data'}))
                self.assertEqual([r.status_code for r in replies], [200, 200])
                for _ in range(4):
                    self.assertEqual((await client.post('/policy/review', json={'text': 'privacy personal data'})).status_code, 200)
                self.assertEqual((await client.post('/policy/review', json={'text': 'privacy personal data'})).status_code, 429)
                self.assertLessEqual(fake.peak, 2)
        asyncio.run(run())

    def test_direct_adapter_output_cap_no_retry_and_no_fallback(self):
        class SDK:
            def __init__(self):
                self.chat = SimpleNamespace(completions=self)
                self.requests = []
                self.options = []
            def with_options(self, **options):
                self.options.append(options)
                return self
            async def create(self, **request):
                self.requests.append(request)
                payload = json.loads(request['messages'][1]['content'])
                content = json.dumps({'proposals': [{'action_id': next(iter(payload['actions'])),
                    'fact_ids': [payload['facts'][0]['id']], 'source_ids': [payload['sources'][0]['id']]}], 'questions': []})
                return SimpleNamespace(usage={'prompt_tokens': 5, 'completion_tokens': 5}, choices=[
                    SimpleNamespace(finish_reason='stop', message=SimpleNamespace(content=content))])
            async def close(self):
                pass
        adapter = object.__new__(OpenAIClient)
        adapter._client = SDK()
        adapter._provider = PROVIDERS['nebius']
        adapter.provider_name = 'nebius'
        adapter._closed = False
        from frontrow.server import create_app
        from frontrow.config import Config
        with patch.dict('os.environ', {'FRONTROW_LLM': 'fake', 'FRONTROW_TTS': 'none',
                'FRONTROW_STT': 'none', 'FRONTROW_POLICY_LLM': 'off', 'FRONTROW_POLICY_COORDINATION': 'configured'}):
            app = create_app(config=Config.from_env(provider='nebius'), llm_factory=lambda: FallbackLLM(adapter))
            with TestClient(app) as client:
                self.assertTrue(client.get('/policy/coordination/status').json()['enabled'])
                exercise = create(client)
                result = client.post(f'/policy/exercises/{exercise}/coordinate', json={'expected_stage': 1})
                self.assertEqual(result.status_code, 200, result.text)
                self.assertEqual(result.json()['review_mode'], 'model_assisted')
            self.assertEqual(len(adapter._client.requests), 3)
            self.assertTrue(all(r['max_tokens'] == 400 for r in adapter._client.requests))
            self.assertTrue(all(r['extra_body']['chat_template_kwargs']['enable_thinking'] is False for r in adapter._client.requests))
            self.assertEqual(adapter._client.options, [{'max_retries': 0}] * 3)
            self.assertTrue(adapter._closed)
            with self.assertRaisesRegex(RuntimeError, 'Anthropic/fake are unsupported'):
                create_app(llm_factory=FakeLLM)


if __name__ == '__main__':
    unittest.main()
