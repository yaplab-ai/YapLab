"""Adversarial response diagnostics and contract checks. Entirely offline."""
from __future__ import annotations

import asyncio
import copy
import importlib.util
import json
from pathlib import Path
from typing import Literal
import unittest
from unittest.mock import patch

from pydantic import BaseModel, ValidationError

from frontrow.llm.base import LLMClient
from frontrow.policy import coordination
from frontrow.policy.coordination import PROTOCOL_VERSION, _schema_issue, _validate_response, coordinate, prepare_role_requests, response_schema
from frontrow.policy.diagnostics import InvalidRoleResponse, VALIDATION_ISSUES
from frontrow.policy.evidence import load_corpus
from frontrow.policy.scenarios import ExerciseStore
from verify_policy_coordination import Scripted, snapshot

PRIVATE = 'PRIVATE-SENTINEL-person@example.invalid'


class Raw(LLMClient):
    def __init__(self, value):
        self.value = value

    async def complete(self, system, user, *, model, timeout):
        if isinstance(self.value, Exception):
            raise self.value
        return self.value


class ValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.corpus = load_corpus()
        cls.state = snapshot()
        cls.request = prepare_role_requests(cls.corpus, cls.state)[0]
        cls.valid = {'proposals': [{'action_id': cls.request['action_ids'][0],
            'fact_ids': [cls.request['fact_ids'][0]], 'source_ids': [cls.request['source_ids'][0]]}],
            'questions': [cls.request['question_ids'][0]]}

    def fixture(self, change):
        data = copy.deepcopy(self.valid)
        change(data)
        return json.dumps(data)

    def rejected(self, raw, expected):
        with self.assertRaises(InvalidRoleResponse) as raised:
            _validate_response(raw, self.request, self.state['scenario_id'])
        self.assertEqual(raised.exception.category, expected)
        self.assertEqual(str(raised.exception), expected)
        self.assertNotIn(PRIVATE, str(vars(raised.exception)))

    def test_strict_json_categories_without_payload_disclosure(self):
        for raw, expected in [
            ({'secret': PRIVATE}, 'non_text_response'),
            (PRIVATE * 1000, 'response_too_large'),
            ('{"' + PRIVATE + '":', 'json_syntax'),
            ('{"proposals":[],"questions":["' + PRIVATE + '"],"questions":[]}', 'duplicate_json_keys'),
            ('{"proposals":[{"action_id":"' + PRIVATE + '","action_id":"x"}],"questions":[]}', 'duplicate_json_keys'),
            ('{"proposals":[],"questions":[NaN]}', 'nonfinite_json_value'),
            ('{"proposals":[],"questions":[Infinity]}', 'nonfinite_json_value'),
            ('{"proposals":[],"questions":[-Infinity]}', 'nonfinite_json_value'),
            ('{"proposals":[],"questions":[1e999]}', 'json_number_limit'),
            ('{"proposals":[],"questions":[' + '7' * 5000 + ']}', 'json_number_limit'),
        ]:
            with self.subTest(category=expected):
                self.rejected(raw, expected)

    def test_schema_categories_are_fixed_not_error_details(self):
        cases = [
            (lambda d: d.update({PRIVATE: PRIVATE}), 'schema_extra_fields'),
            (lambda d: d.pop('questions'), 'schema_missing_fields'),
            (lambda d: d.update(questions={'secret': PRIVATE}), 'schema_types'),
            (lambda d: d.update(questions=[True]), 'schema_types'),
            (lambda d: d['proposals'][0].update(action_id=3), 'schema_types'),
            (lambda d: d.update(proposals=d['proposals'] * 3), 'schema_limits'),
            (lambda d: d['proposals'][0].update(fact_ids=['x'] * 4), 'schema_limits'),
            (lambda d: d['proposals'][0].update(source_ids=['x'] * 3), 'schema_limits'),
            (lambda d: d.update(questions=['x'] * 3), 'schema_limits'),
            (lambda d: d['proposals'][0].update(action_id='x' * 81), 'schema_limits'),
        ]
        for change, expected in cases:
            with self.subTest(category=expected):
                self.rejected(self.fixture(change), expected)
        class FutureContract(BaseModel):
            value: Literal['allowed']
        try:
            FutureContract.model_validate({'value': PRIVATE})
        except ValidationError as error:
            self.assertEqual(_schema_issue(error), 'schema_contract')

    def test_duplicate_and_unknown_ids_are_classified_separately(self):
        cases = [
            (lambda d: d.update(proposals=d['proposals'] * 2), 'duplicate_action_ids'),
            (lambda d: d.update(questions=d['questions'] * 2), 'duplicate_question_ids'),
            (lambda d: d['proposals'][0].update(fact_ids=d['proposals'][0]['fact_ids'] * 2), 'duplicate_fact_ids'),
            (lambda d: d['proposals'][0].update(source_ids=d['proposals'][0]['source_ids'] * 2), 'duplicate_source_ids'),
            (lambda d: d['proposals'][0].update(action_id=PRIVATE), 'unknown_action_id'),
            (lambda d: d['proposals'][0].update(fact_ids=[PRIVATE]), 'unknown_fact_id'),
            (lambda d: d['proposals'][0].update(source_ids=[PRIVATE]), 'unknown_source_id'),
            (lambda d: d.update(questions=[PRIVATE]), 'unknown_question_id'),
        ]
        for change, expected in cases:
            with self.subTest(category=expected):
                self.rejected(self.fixture(change), expected)

    def test_empty_arrays_remain_valid_without_fabrication(self):
        self.assertEqual(_validate_response('{"proposals":[],"questions":[]}', self.request,
                                          self.state['scenario_id']), ([], []))
        valid = copy.deepcopy(self.valid)
        valid['proposals'][0]['fact_ids'] = list(self.request['fact_ids'][:3])
        valid['proposals'][0]['source_ids'] = list(self.request['source_ids'][:2])
        valid['questions'] = list(self.request['question_ids'])
        proposals, questions = _validate_response(json.dumps(valid), self.request, self.state['scenario_id'])
        self.assertEqual(proposals[0]['fact_ids'], valid['proposals'][0]['fact_ids'])
        self.assertEqual([q['question_id'] for q in questions], valid['questions'])

    def test_contract_enums_match_only_released_role_inputs_in_both_scopes(self):
        for scenario in ('transcript-disclosure', 'caption-failure', 'feedback-as-grade'):
            for stage in (1, 2, 3):
                state = snapshot(scenario, stage)
                for institution in ('general', 'uaeu'):
                    for request in prepare_role_requests(self.corpus, state, institution):
                        payload = json.loads(request['user'])
                        self.assertEqual(payload['protocol_version'], PROTOCOL_VERSION)
                        allowed = payload['allowed_ids']
                        for key in ('action_ids', 'fact_ids', 'source_ids', 'question_ids'):
                            self.assertEqual(allowed[key], list(request[key]))
                        self.assertEqual(allowed['fact_ids'], [f['id'] for f in state['role_views'][request['role']]])
                        contract = payload['response_schema']
                        properties = contract['properties']
                        proposal = properties['proposals']['items']
                        self.assertFalse(contract['additionalProperties'])
                        self.assertFalse(proposal['additionalProperties'])
                        self.assertEqual(set(contract['required']), {'proposals', 'questions'})
                        self.assertEqual(set(proposal['required']), {'action_id', 'fact_ids', 'source_ids'})
                        self.assertEqual(proposal['properties']['action_id']['enum'], allowed['action_ids'])
                        for field in ('fact_ids', 'source_ids'):
                            self.assertTrue(proposal['properties'][field]['uniqueItems'])
                            self.assertEqual(proposal['properties'][field]['items']['enum'], allowed[field])
                        self.assertEqual(properties['questions']['items']['enum'], allowed['question_ids'])
                        self.assertTrue(properties['questions']['uniqueItems'])
                        self.assertEqual(payload['empty_response'], {'proposals': [], 'questions': []})
                        self.assertIn('at most once', request['system'])
                        self.assertIn('never question text or objects', request['system'])

    def test_no_candidates_contract_uses_false_schema_not_empty_enum(self):
        schema = response_schema((), (), (), ())
        self.assertFalse(schema['properties']['questions']['items'])
        self.assertFalse(schema['properties']['proposals']['items']['properties']['action_id'])

    def test_provider_exceptions_are_not_model_validation_failures(self):
        async def check():
            for error in (ValueError(PRIVATE), TypeError(PRIVATE), RuntimeError(PRIVATE)):
                result = await coordinate(self.corpus, self.state, Raw(error), 'offline')
                self.assertTrue(all(r['reason'] == 'provider_error' for r in result['roles']))
                self.assertTrue(all('validation_issue' not in r for r in result['roles']))
                self.assertNotIn(PRIVATE, json.dumps(result))
        asyncio.run(check())

    def test_unexpected_validator_defect_is_not_blame_for_model(self):
        async def check():
            with patch.object(coordination, '_validate_response', side_effect=ValueError(PRIVATE)):
                result = await coordinate(self.corpus, self.state, Raw(json.dumps(self.valid)), 'offline')
            self.assertTrue(all(r['reason'] == 'validation_error' for r in result['roles']))
            self.assertTrue(all('validation_issue' not in r for r in result['roles']))
            self.assertNotIn(PRIVATE, json.dumps(result))
        asyncio.run(check())

    def test_diagnostic_persists_without_raw_response_or_other_role_details(self):
        class OneInvalid(Scripted):
            async def complete(self, system, user, *, model, timeout):
                if json.loads(user)['role'] == 'teacher':
                    return self_invalid
                return await super().complete(system, user, model=model, timeout=timeout)
        self_invalid = self.fixture(lambda d: d['proposals'][0].update(fact_ids=[PRIVATE]))
        store = ExerciseStore()
        exercise = store.create('caption-failure', 'teacher')['exercise_id']
        reserved = store.reserve_coordination(exercise, 1, 'general')
        state = {k: reserved[k] for k in ('scenario_id', 'stage', 'role_views')}
        result = asyncio.run(coordinate(self.corpus, state, OneInvalid(), 'offline'))
        saved = store.commit_coordination(exercise, reserved['round_id'], result)
        teacher = store.audit(exercise, 'teacher')['events'][0]['assessment']
        privacy = store.audit(exercise, 'privacy')['events'][0]['assessment']
        self.assertEqual(teacher['validation_issue'], 'unknown_fact_id')
        self.assertNotIn('validation_issue', privacy)
        self.assertNotIn(PRIVATE, json.dumps([saved, teacher, privacy]))

    def test_historical_live_evidence_remains_v1_with_unknown_rejection_categories(self):
        path = Path(__file__).resolve().parents[2] / 'docs/evidence/ai-for-good-coordination-live-2026-11-04.json'
        record = json.loads(path.read_text())
        self.assertEqual(record['protocol_version'], '1')
        accepted = rejected = 0
        for item in record['snapshots']:
            requests = {r['role']: r for r in prepare_role_requests(self.corpus, snapshot(item['scenario_id'], item['stage']))}
            for role in item['roles']:
                self.assertNotIn('validation_issue', role)
                if role['status'] == 'completed':
                    _validate_response(json.dumps({'proposals': role['proposals'], 'questions': role['question_ids']}),
                                       requests[role['role']], item['scenario_id'])
                    accepted += 1
                else:
                    self.assertEqual(role['reason'], 'invalid_response')
                    rejected += 1
        self.assertEqual((accepted, rejected), (14, 13))

    def test_unknown_category_cannot_store_exception_text(self):
        self.assertEqual(len(VALIDATION_ISSUES), 19)
        with self.assertRaisesRegex(ValueError, '^Unknown validation category$'):
            InvalidRoleResponse(PRIVATE)


if __name__ == '__main__':
    unittest.main()
