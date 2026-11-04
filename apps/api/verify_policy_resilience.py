"""Offline partial-role validation and evidence isolation regressions."""
from __future__ import annotations

import asyncio
import copy
import json
import unittest

from frontrow.policy.coordination import _assess_response, _validate_response, coordinate, prepare_role_requests
from frontrow.policy.diagnostics import InvalidRoleResponse
from frontrow.policy.evidence import load_corpus
from verify_policy_coordination import Scripted, snapshot

PRIVATE = 'PRIVATE-HIDDEN-person@example.invalid'


class ResilienceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.corpus = load_corpus()
        cls.state = snapshot('caption-failure', 2)
        cls.request = prepare_role_requests(cls.corpus, cls.state)[0]
        cls.scenario = cls.state['scenario_id']
        cls.valid = {'action_id': cls.request['action_ids'][0],
                     'fact_ids': [cls.request['fact_ids'][0]],
                     'source_ids': [cls.request['source_ids'][0]]}

    def assess(self, proposals, questions):
        return _assess_response(json.dumps({'proposals': proposals, 'questions': questions}), self.request, self.scenario)

    def test_good_sibling_survives_unknown_source(self):
        bad = dict(self.valid, action_id=self.request['action_ids'][1], source_ids=[PRIVATE])
        proposals, questions, issue = self.assess([self.valid, bad], [])
        self.assertEqual(issue, 'unknown_source_id')
        self.assertEqual([p['action_id'] for p in proposals], [self.valid['action_id']])
        self.assertEqual(proposals[0]['source_ids'], self.valid['source_ids'])
        self.assertEqual(questions, [])
        self.assertNotIn(PRIVATE, str((proposals, questions, issue)))
        with self.assertRaises(InvalidRoleResponse):
            _validate_response(json.dumps({'proposals': [self.valid, bad], 'questions': []}), self.request, self.scenario)

    def test_duplicate_keeps_first_valid_evidence_without_merging(self):
        duplicate = dict(self.valid, fact_ids=[self.request['fact_ids'][1]], source_ids=[self.request['source_ids'][1]])
        proposals, _, issue = self.assess([self.valid, duplicate], [])
        self.assertEqual(issue, 'duplicate_action_ids')
        self.assertEqual(len(proposals), 1)
        self.assertEqual(proposals[0]['fact_ids'], self.valid['fact_ids'])
        self.assertEqual(proposals[0]['source_ids'], self.valid['source_ids'])
        # An invalid earlier attempt cannot suppress a later valid item.
        invalid = dict(self.valid, source_ids=[PRIVATE])
        proposals, _, issue = self.assess([invalid, duplicate], [])
        self.assertEqual(issue, 'unknown_source_id')
        self.assertEqual(proposals[0]['fact_ids'], duplicate['fact_ids'])
        self.assertEqual(proposals[0]['source_ids'], duplicate['source_ids'])

    def test_three_distinct_proposals_are_bounded_to_two(self):
        items = [dict(self.valid, action_id=action) for action in self.request['action_ids'][:3]]
        self.assertEqual(len(items), 3)
        proposals, _, issue = self.assess(items, [])
        self.assertEqual(issue, 'schema_limits')
        self.assertEqual([p['action_id'] for p in proposals], list(self.request['action_ids'][:2]))

    def test_questions_retained_independently(self):
        good = self.request['question_ids'][0]
        _, questions, issue = self.assess([], [good, PRIVATE, good, {'hidden': PRIVATE}])
        self.assertEqual(issue, 'unknown_question_id')
        self.assertEqual([q['question_id'] for q in questions], [good])
        self.assertNotIn(PRIVATE, str(questions))
        _, questions, issue = self.assess([], list(self.request['question_ids']) + [good])
        self.assertEqual(issue, 'duplicate_question_ids')
        self.assertEqual(len(questions), 2)

    def test_malformed_or_invalid_envelopes_never_salvage(self):
        for raw, issue in [
            ('{"proposals":[],"questions":[],"questions":[]}', 'duplicate_json_keys'),
            ('{"proposals":[],"questions":[NaN]}', 'nonfinite_json_value'),
            ('{"proposals":[],"questions":', 'json_syntax'),
            (json.dumps({'proposals': [self.valid], 'questions': [], PRIVATE: PRIVATE}), 'schema_extra_fields'),
            (json.dumps({'proposals': [self.valid], 'questions': PRIVATE}), 'schema_types'),
        ]:
            with self.subTest(issue=issue):
                with self.assertRaises(InvalidRoleResponse) as exc:
                    _assess_response(raw, self.request, self.scenario)
                self.assertEqual(exc.exception.category, issue)
                self.assertNotIn(PRIVATE, str(exc.exception))

    def test_incident_candidates_focus_on_operational_notes(self):
        context_only = {'uae-inclusive-education-schools', 'uae-national-ai-strategy-2031'}
        self.assertTrue(context_only <= {source.id for source in self.corpus.entries})
        for stage in (1, 2, 3):
            for scenario, relevant in (
                    ('transcript-disclosure', 'uae-personal-data-protection'),
                    ('feedback-as-grade', 'england-generative-ai-education')):
                prepared = prepare_role_requests(self.corpus, snapshot(scenario, stage))
                teacher = next(item for item in prepared if item['role'] == 'teacher')
                self.assertIn(relevant, teacher['source_ids'])
                for request in prepared:
                    self.assertFalse(context_only & set(request['source_ids']))
                    payload = json.loads(request['user'])
                    for source in payload['sources']:
                        self.assertTrue(source['source_locator'])
                        self.assertTrue(source['verification'])
                        self.assertEqual(source, {k: v for k, v in next(
                            entry for entry in request['evidence'] if entry['id'] == source['id']).items()
                            if k != 'sha256'})
        # These checks establish candidate availability, not source applicability.

    def test_context_only_collection_abstains_without_model_calls(self):
        context = self.corpus.model_copy(update={'entries': [source for source in self.corpus.entries
            if source.id in {'uae-inclusive-education-schools', 'uae-national-ai-strategy-2031'}]})
        client = Scripted()
        result = asyncio.run(coordinate(context, self.state, client, 'offline'))
        self.assertEqual(client.requests, [])
        self.assertTrue(all(role['reason'] == 'insufficient_evidence' and not role['proposals']
                            for role in result['roles']))

    def test_role_status_and_no_hidden_output(self):
        def mixed(out, payload):
            valid = out['proposals'][0]
            bad = dict(valid, action_id=payload['allowed_ids']['action_ids'][1], source_ids=[PRIVATE])
            out['proposals'] = [valid, bad]
            return out
        def all_bad(out, payload):
            out['proposals'][0]['fact_ids'] = [PRIVATE]
            return out
        def question_only(out, payload):
            out['proposals'][0]['source_ids'] = [PRIVATE]
            out['questions'] = [payload['allowed_ids']['question_ids'][0]]
            return out
        async def run():
            for mutate, expected, valid_proposals, valid_questions in [
                    (mixed, 'partial', 1, 0), (all_bad, 'unavailable', 0, 0),
                    (question_only, 'partial', 0, 1)]:
                result = await coordinate(self.corpus, self.state, Scripted({'teacher': mutate}), 'offline')
                teacher = next(role for role in result['roles'] if role['role'] == 'teacher')
                self.assertEqual(teacher['status'], expected)
                self.assertEqual(teacher['reason'], 'invalid_response')
                self.assertIn(teacher['validation_issue'], {'unknown_fact_id', 'unknown_source_id'})
                self.assertEqual(len(teacher['proposals']), valid_proposals)
                self.assertEqual(len(teacher['questions']), valid_questions)
                self.assertNotIn(PRIVATE, json.dumps(result))
        asyncio.run(run())


if __name__ == '__main__':
    unittest.main()
