"""Protocol 4 and recorded-live audit tests; no provider calls."""
from __future__ import annotations

import asyncio
import json
import unittest
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from frontrow.llm.openai_client import OpenAIClient
from frontrow.policy.audit import validate_recording, render_html
from frontrow.policy.coordination import _assess_response, coordinate, prepare_role_requests
from frontrow.policy.evidence import load_corpus
from frontrow.policy.router import create_router, ModelCallLimits
from frontrow.limits import LimitExceeded
from frontrow.policy.scenarios import ExerciseStore, Decision, router as scenarios_router
from verify_policy_coordination import Scripted, snapshot


class ProtocolAuditTests(unittest.TestCase):
    def test_explicit_synthetic_evaluation_budget_is_bounded(self):
        limits = ModelCallLimits(evaluation_limit=27)
        for _ in range(9):
            limits.reserve('loopback-test', 3)
        with self.assertRaises(LimitExceeded):
            limits.reserve('loopback-test', 1)
        for bad in (0, 61, True):
            with self.assertRaises(ValueError):
                ModelCallLimits(evaluation_limit=bad)

    def test_rationale_rejection_preserves_proposal(self):
        request = prepare_role_requests(load_corpus(), snapshot())[0]
        base = {'action_id': request['action_ids'][0], 'fact_ids': [request['fact_ids'][0]],
                'source_ids': [request['source_ids'][0]]}
        uncited_source = next(source for source in request['known_source_ids'] if source not in base['source_ids'])
        uncited_fact = next(fact for fact in request['fact_ids'] if fact not in base['fact_ids'])
        for text, label in [(None, 'rationale_missing'), ('x' * 201, 'rationale_length'),
                            ('https://example.org', 'rationale_url'), ('**bold**', 'rationale_markdown'),
                            ('This is illegal', 'rationale_legal_conclusion'),
                            ('Data protection law supports restricting access.', 'rationale_legal_conclusion'),
                            ('Review ' + uncited_source, 'rationale_uncited_id'),
                            ('Review ' + uncited_fact.upper(), 'rationale_uncited_id')]:
            item = dict(base)
            if text is not None:
                item['rationale'] = text
            proposals, _, issue = _assess_response(json.dumps({'proposals': [item], 'questions': []}), request, 'caption-failure')
            self.assertIsNone(issue)
            self.assertEqual(len(proposals), 1)
            self.assertEqual(proposals[0]['action_id'], base['action_id'])
            self.assertEqual(proposals[0]['rationale_issue'], label)
            self.assertTrue(proposals[0]['rationale_rejected'])
            self.assertNotIn('rationale', proposals[0])
        for text in ('The missing captions prevent equal participation, so pause until an accessible option is confirmed.',
                     'Use a human-centred and role-specific response.',
                     'Check ' + base['fact_ids'][0] + ' and ' + base['source_ids'][0] + ' before a human decision.'):
            item = dict(base, rationale=text)
            proposals, _, _ = _assess_response(json.dumps({'proposals': [item], 'questions': []}), request, 'caption-failure')
            self.assertEqual(proposals[0]['rationale'], text)

    def test_html_timeline_is_ordered_readable_and_escaped(self):
        audit = {'scenario_id': 'caption-failure', 'exercise_id': 'exercise', 'current_stage': 1, 'sha256': 'audit-hash',
                 'events': [
                     {'type': 'stage_release', 'stage': 1, 'at': 'time-1', 'fact_ids_by_role': {'teacher': ['cf-1a']}},
                     {'type': 'model_request', 'stage': 1, 'at': 'time-2', 'role': 'teacher',
                      'provider': 'nebius', 'model': '<script>bad()</script>', 'review_mode': 'model_assisted',
                      'status': 'success', 'prompt_sha256': 'prompt-hash', 'usage': {'prompt_tokens': 12},
                      'latency_ms': 42, 'evidence_refs': [{'id': 'source', 'sha256': 'evidence-hash'}]},
                     {'type': 'validation', 'stage': 1, 'at': 'time-3', 'role': 'teacher', 'status': 'partial',
                      'issue': 'unknown_action_id', 'rationale_issues': ['rationale_missing']},
                     {'type': 'coordinator_plan', 'stage': 1, 'at': 'time-4', 'plan': [
                         {'action_id': 'pause', 'owner': 'teacher', 'status': 'missing_prerequisites', 'handoffs': []}],
                      'unresolved': ['Check with privacy']},
                     {'type': 'decision', 'stage': 1, 'at': 'time-5', 'role': 'teacher',
                      'review_mode': 'human_decision', 'decision': '<img src=x onerror=bad()>', 'source_ids': ['cf-1a']}]}
        page = render_html(audit)
        visible = page.split('<ol>', 1)[1].split('</ol>', 1)[0]
        headings = ['Stage released', 'Model request', 'Validation', 'Coordinator plan', 'Human decision']
        self.assertEqual(sorted(headings, key=visible.index), headings)
        for expected in ('cf-1a', 'nebius', 'model_assisted', 'prompt-hash', 'evidence-hash',
                         'prompt_tokens', '42', 'unknown_action_id', 'missing_prerequisites', 'teacher'):
            self.assertIn(expected, visible)
        self.assertIn('audit-hash', page)
        self.assertIn('&lt;script&gt;bad()&lt;/script&gt;', visible)
        self.assertIn('&lt;img src=x onerror=bad()&gt;', visible)
        self.assertNotIn('<script>', page)
        self.assertNotIn('<img ', page)
        self.assertIn('<summary>Complete audit JSON</summary>', page)

    def test_export_and_recorded_replay_do_not_call_provider(self):
        class MockLive(OpenAIClient):
            def __init__(self):
                self.provider_name = 'nebius'
                self.scripted = Scripted()
            async def complete(self, system, user, *, model, timeout):
                return await self.scripted.complete(system, user, model=model, timeout=timeout)
        store = ExerciseStore()
        created = store.create('caption-failure', 'teacher')
        exercise = created['exercise_id']
        client = MockLive()
        async def save():
            for stage in (1, 2, 3):
                if stage > 1:
                    store.advance(exercise, 'teacher', stage - 1)
                snap = store.reserve_coordination(exercise, stage, 'general')
                result = await coordinate(load_corpus(), {k: snap[k] for k in ('scenario_id', 'stage', 'role_views')},
                    client, 'nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B', mode='model_assisted')
                store.commit_coordination(exercise, snap['round_id'], result)
            store.decide(exercise, Decision(role='teacher', decision='Review with the team', source_ids=['cf-1a'], expected_stage=3))
        asyncio.run(save())
        export = store.timeline(exercise)
        self.assertEqual([e['stage'] for e in export['events'] if e['type'] == 'stage_release'], [1, 2, 3])
        self.assertEqual(len([e for e in export['events'] if e['type'] == 'model_request']), 9)
        self.assertEqual(len([e for e in export['events'] if e['type'] == 'validation']), 9)
        self.assertEqual(len([e for e in export['events'] if e['type'] == 'coordinator_plan']), 3)
        self.assertEqual(export['events'][-1]['source_ids'], ['cf-1a'])
        self.assertEqual(validate_recording(export)['recording'], export)
        modified = json.loads(json.dumps(export)); modified['current_stage'] = 1
        with self.assertRaises(ValueError): validate_recording(modified)
        self.assertNotIn('<script>', render_html({'x': '<script>'}))
        app = FastAPI(); app.include_router(scenarios_router); app.include_router(create_router())
        http = TestClient(app)
        with patch.object(client, 'complete', side_effect=AssertionError('network call')):
            result = http.post('/policy/replays', json=export)
            self.assertEqual(result.status_code, 200)
            replay = result.json()
            self.assertIn('no new model calls', replay['banner'])
            self.assertEqual(replay['recording'], export)
            self.assertEqual(http.get('/policy/replays/' + replay['replay_id']).json()['recording'], export)
            self.assertEqual(http.post('/policy/replays', json=modified).status_code, 422)
            self.assertEqual(http.post('/policy/exercises/' + replay['replay_id'] + '/advance', json={'expected_stage': 1}).status_code, 404)


if __name__ == '__main__': unittest.main()
