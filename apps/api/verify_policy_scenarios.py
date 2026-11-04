"""Offline regression checks for staged synthetic policy exercises.

Run from apps/api: .venv/bin/python verify_policy_scenarios.py
"""
from concurrent.futures import ThreadPoolExecutor
import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

from frontrow.policy import scenarios


def make_client(store=None):
    app = FastAPI()
    app.include_router(scenarios.router)
    if store is not None:
        app.state.policy_exercise_store = store
    return TestClient(app)


def check_disclosure_and_audit():
    with make_client() as client:
        metadata = client.get('/policy/scenarios').json()
        assert len(metadata['scenarios']) == 3
        metadata_text = json.dumps(metadata)
        for scenario in scenarios._SCENARIOS:
            for stage in scenario['stages']:
                for fact in stage['facts']:
                    assert fact['text'] not in metadata_text
            response = client.post('/policy/exercises', json={'scenario_id': scenario['id']})
            assert response.status_code == 200, response.text
            created = response.json()
            assert created['current_stage'] == 1 and len(created['released_stages']) == 1
            # Even role-specific views expose neither later facts nor stage titles.
            for role in scenarios.ROLES:
                view = client.get(f"/policy/exercises/{created['exercise_id']}", params={'role': role}).json()
                text = json.dumps(view)
                for future in scenario['stages'][1:]:
                    assert future['title'] not in text
                    assert all(fact['text'] not in text and fact['id'] not in text for fact in future['facts'])
                visible_ids = {fact['id'] for stage in view['released_stages'] for fact in stage['facts']}
                expected_ids = {fact['id'] for fact in scenario['stages'][0]['facts'] if role in fact['roles']}
                assert visible_ids == expected_ids
                assert all('roles' not in fact for stage in view['released_stages'] for fact in stage['facts'])

        exercise = client.post('/policy/exercises', json={'scenario_id': 'transcript-disclosure'}).json()
        path = f"/policy/exercises/{exercise['exercise_id']}"
        teacher = client.get(path, params={'role': 'teacher'}).json()
        accessibility = client.get(path, params={'role': 'accessibility'}).json()
        teacher_ids = {f['id'] for s in teacher['released_stages'] for f in s['facts']}
        access_ids = {f['id'] for s in accessibility['released_stages'] for f in s['facts']}
        assert 'td-1b' in teacher_ids and 'td-1b' not in access_ids
        assert 'td-1c' in access_ids and 'td-1c' not in teacher_ids
        assert client.post(path + '/decision', json={'role': 'teacher', 'decision': 'Pause sharing', 'source_ids': ['td-2a'], 'expected_stage': 1}).status_code == 422
        assert client.post(path + '/decision', json={'role': 'teacher', 'decision': 'Pause sharing', 'source_ids': ['td-1c'], 'expected_stage': 1}).status_code == 422
        assert client.post(path + '/decision', json={'role': 'teacher', 'decision': 'Pause sharing', 'source_ids': ['td-1b'], 'expected_stage': 1}).status_code == 200
        assert client.post(path + '/decision', json={'role': 'accessibility', 'decision': 'Ask privately', 'source_ids': ['td-1c'], 'expected_stage': 1}).status_code == 200
        assert client.post(path + '/decision', json={'role': 'teacher', 'decision': ' ', 'source_ids': ['td-1b'], 'expected_stage': 1}).status_code == 422
        assert client.post(path + '/decision', json={'role': 'teacher', 'decision': 'x' * 501, 'source_ids': ['td-1b'], 'expected_stage': 1}).status_code == 422
        for body in ({}, {'expected_stage': 0}, {'expected_stage': '1'},
                     {'expected_stage': True}, {'expected_stage': 1, 'extra': 1}):
            assert client.post(path + '/advance', json=body).status_code == 422
        for body in (
            {'role': 'teacher', 'decision': 'Act', 'source_ids': ['td-1b']},
            {'role': 'teacher', 'decision': 'Act', 'expected_stage': 1},
            {'role': 'teacher', 'decision': 'Act', 'source_ids': [], 'expected_stage': 1},
            {'role': 'teacher', 'decision': 'Act', 'source_ids': ['td-1b'], 'expected_stage': True},
            {'role': 'teacher', 'decision': 'Act', 'source_ids': ['td-1b'], 'expected_stage': 1, 'extra': 1},
        ):
            assert client.post(path + '/decision', json=body).status_code == 422
        assert client.get(path, params={'role': 'administrator'}).status_code == 422
        assert client.post(path + '/decision', json={'role': 'administrator', 'decision': 'x', 'source_ids': ['td-1b'], 'expected_stage': 1}).status_code == 422
        assert client.post(path + '/advance', json={'expected_stage': 1}).json()['current_stage'] == 2
        assert client.post(path + '/decision', json={'role': 'teacher', 'decision': 'Check audience', 'source_ids': ['td-2a'], 'expected_stage': 2}).status_code == 200
        assert client.post(path + '/advance', json={'expected_stage': 2}).json()['current_stage'] == 3
        assert client.post(path + '/advance', json={'expected_stage': 3}).status_code == 409
        audit_teacher = client.get(path + '/audit', params={'role': 'teacher'}).json()['events']
        audit_access = client.get(path + '/audit', params={'role': 'accessibility'}).json()['events']
        assert 'Ask privately' not in json.dumps(audit_teacher)
        assert 'Pause sharing' not in json.dumps(audit_access)
        assert [e['stage'] for e in audit_teacher if e['type'] == 'advance'] == [2, 3]
        assert client.get('/policy/exercises/no-such-id').status_code == 404
        assert client.post('/policy/exercises', json={'scenario_id': 'no-such-id'}).status_code == 404


def check_ttl_capacity_actions_and_concurrency():
    now = [10.0]
    store = scenarios.ExerciseStore(ttl=5, capacity=1, max_actions=1, clock=lambda: now[0])
    with make_client(store) as client:
        first = client.post('/policy/exercises', json={'scenario_id': 'caption-failure'}).json()
        path = f"/policy/exercises/{first['exercise_id']}"
        assert client.post('/policy/exercises', json={'scenario_id': 'caption-failure'}).status_code == 429
        assert client.post(path + '/advance', json={'expected_stage': 1}).status_code == 200
        assert client.post(path + '/advance', json={'expected_stage': 2}).status_code == 429
        assert client.post(path + '/decision', json={'role': 'teacher', 'decision': 'Act', 'source_ids': ['cf-1a'], 'expected_stage': 2}).status_code == 429
        now[0] = 15.0
        assert client.get(path).status_code == 404
        assert client.get(path + '/audit').status_code == 404
        assert client.post(path + '/advance', json={'expected_stage': 2}).status_code == 404
        assert client.post(path + '/decision', json={'role': 'teacher', 'decision': 'Act', 'source_ids': ['cf-1a'], 'expected_stage': 2}).status_code == 404
        assert client.post('/policy/exercises', json={'scenario_id': 'caption-failure'}).status_code == 200

    with make_client() as client:
        exercise_id = client.post('/policy/exercises', json={'scenario_id': 'feedback-as-grade'}).json()['exercise_id']
        path = f'/policy/exercises/{exercise_id}'
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: client.post(path + '/advance', json={'expected_stage': 1}), range(2)))
        assert sorted(result.status_code for result in results) == [200, 409]
        assert next(result for result in results if result.status_code == 200).json()['current_stage'] == 2
        assert 'refresh' in next(result for result in results if result.status_code == 409).json()['detail'].lower()
        stale = client.post(path + '/decision', json={'role': 'teacher', 'decision': 'Stale',
                                                       'source_ids': ['fg-1a'], 'expected_stage': 1})
        assert stale.status_code == 409 and 'refresh' in stale.json()['detail'].lower()
        assert [e['type'] for e in client.get(path + '/audit').json()['events']] == ['advance']
        fresh = client.post(path + '/decision', json={'role': 'teacher', 'decision': 'Fresh',
                                                       'source_ids': ['fg-1a'], 'expected_stage': 2})
        assert fresh.status_code == 200 and fresh.json()['event']['stage'] == 2
        assert [e['type'] for e in client.get(path + '/audit').json()['events']] == ['advance', 'decision']


def check_admission():
    with make_client() as client:
        def create(_):
            return client.post('/policy/exercises', json={'scenario_id': 'caption-failure'})
        with ThreadPoolExecutor(max_workers=12) as pool:
            results = list(pool.map(create, range(35)))
        assert sum(response.status_code == 200 for response in results) == 30
        denied = [response for response in results if response.status_code == 429]
        assert len(denied) == 5 and all(int(response.headers['retry-after']) > 0 for response in denied)
        assert len(client.app.state.policy_exercise_store.exercises) == 30
        successful = next(response for response in results if response.status_code == 200)
        assert successful.headers['cache-control'] == 'no-store'
        exercise_id = successful.json()['exercise_id']
        assert client.get(f'/policy/exercises/{exercise_id}').headers['cache-control'] == 'no-store'


if __name__ == '__main__':
    check_disclosure_and_audit()
    check_ttl_capacity_actions_and_concurrency()
    check_admission()
    print('Policy scenario checks passed')
