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
        assert client.post(path + '/decision', json={'role': 'teacher', 'decision': 'Pause sharing', 'source_ids': ['td-2a']}).status_code == 422
        assert client.post(path + '/decision', json={'role': 'teacher', 'decision': 'Pause sharing', 'source_ids': ['td-1c']}).status_code == 422
        assert client.post(path + '/decision', json={'role': 'teacher', 'decision': 'Pause sharing', 'source_ids': ['td-1b']}).status_code == 200
        assert client.post(path + '/decision', json={'role': 'accessibility', 'decision': 'Ask privately', 'source_ids': ['td-1c']}).status_code == 200
        assert client.post(path + '/decision', json={'role': 'teacher', 'decision': ' '}).status_code == 422
        assert client.post(path + '/decision', json={'role': 'teacher', 'decision': 'x' * 501}).status_code == 422
        assert client.get(path, params={'role': 'administrator'}).status_code == 422
        assert client.post(path + '/decision', json={'role': 'administrator', 'decision': 'x'}).status_code == 422
        assert client.post(path + '/advance').json()['current_stage'] == 2
        assert client.post(path + '/decision', json={'role': 'teacher', 'decision': 'Check audience', 'source_ids': ['td-2a']}).status_code == 200
        assert client.post(path + '/advance').json()['current_stage'] == 3
        assert client.post(path + '/advance').status_code == 409
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
        assert client.post(path + '/advance').status_code == 200
        assert client.post(path + '/advance').status_code == 429
        assert client.post(path + '/decision', json={'role': 'teacher', 'decision': 'Act'}).status_code == 429
        now[0] = 15.0
        assert client.get(path).status_code == 404
        assert client.get(path + '/audit').status_code == 404
        assert client.post(path + '/advance').status_code == 404
        assert client.post(path + '/decision', json={'role': 'teacher', 'decision': 'Act'}).status_code == 404
        assert client.post('/policy/exercises', json={'scenario_id': 'caption-failure'}).status_code == 200

    store = scenarios.ExerciseStore()
    exercise_id = store.create('feedback-as-grade', 'teacher')['exercise_id']
    with ThreadPoolExecutor(max_workers=2) as pool:
        views = list(pool.map(lambda _: store.advance(exercise_id, 'teacher'), range(2)))
    assert sorted(view['current_stage'] for view in views) == [2, 3]
    assert len(store.audit(exercise_id, 'teacher')['events']) == 2


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
