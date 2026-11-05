"""Offline tests: .venv/bin/python verify_policy_outcomes.py"""
import json
import unittest
from pathlib import Path
from frontrow.policy import coordination
from frontrow.policy.gaps import load_gaps
from frontrow.policy.outcomes import load_outcomes, score_role, score, markdown

ROOT = Path(__file__).parent / 'frontrow' / 'policy'

class OutcomeTests(unittest.TestCase):
    def setUp(self):
        self.rubric = load_outcomes()
        self.rows = self.rubric['entries']
        self.row = next(r for r in self.rows if (r['scenario_id'],r['stage'],r['role']) == ('caption-failure',2,'teacher'))
        self.proposal = {'action_id':'resume_vendor_workshop','fact_ids':['cf-2b'],'source_ids':['uae-digital-accessibility-policy']}
        self.role = {'role':'teacher','status':'completed','proposals':[self.proposal], 'evidence':[{'source_id':'uae-digital-accessibility-policy'}]}
        self.plan = [{'action_id':'resume_vendor_workshop','owner':'teacher','status':'missing_prerequisites',
                      'handoffs':[{'action_id':'verify_vendor_terms','owner':'privacy'}, {'action_id':'confirm_accessible_option','owner':'accessibility'}]}]
        self.round = {'scenario_id':'caption-failure','stage':2,'roles':[self.role], 'plan':self.plan}

    def test_complete_matrix_fact_visibility_and_action_release(self):
        scenarios = {x['id']:x for x in json.loads((ROOT/'scenarios.json').read_text())}
        keys = {(r['scenario_id'],r['stage'],r['role']) for r in self.rows}
        self.assertEqual(len(self.rows), 27)
        self.assertEqual(len(keys), 27)
        for row in self.rows:
            scenario, stage, role = row['scenario_id'], row['stage'], row['role']
            facts = {f['id'] for s in scenarios[scenario]['stages'][:stage] for f in s['facts'] if role in f['roles']}
            self.assertTrue(set(row['expected_fact_ids_any']) <= facts, row)
            for action in row['acceptable_action_ids']:
                self.assertLessEqual(coordination._ACTIONS[scenario][role][action][1], stage)
            self.assertTrue(row['expected_source_ids_any'])
            self.assertEqual(row['expected_coordinator']['owner'], role)
        self.assertIn('not expert-validated', self.rubric['label'].lower())

    def test_match_requires_same_proposal_citation_and_correct_prerequisites(self):
        result = score_role(self.row, self.round)
        self.assertEqual(result['rating'], 'match', result['why'])
        self.plan[0]['status'] = 'awaiting_human_confirmation'
        self.assertEqual(score_role(self.row, self.round)['rating'], 'partial')
        self.plan[0]['status'] = 'missing_prerequisites'
        self.plan[0]['handoffs'].pop()
        self.assertEqual(score_role(self.row, self.round)['rating'], 'partial')

    def test_relevant_fact_and_source_must_be_on_accepted_action(self):
        self.role['proposals'] = [dict(self.proposal, fact_ids=['cf-1a']),
                                  {'action_id':'start_workshop_now','fact_ids':['cf-2b'], 'source_ids':['uae-digital-accessibility-policy']}]
        result = score_role(self.row, self.round)
        self.assertEqual(result['rating'], 'partial')
        self.assertTrue(any('fact' in why for why in result['why']))

    def test_source_context_is_explicit_and_partial_status_stays_partial(self):
        self.proposal['source_ids'] = ['other-source']
        self.role['evidence'] = [{'source_id':'other-source'}]
        result = score_role(self.row, self.round)
        self.assertEqual(result['rating'], 'partial')
        self.assertTrue(any('offered' in why for why in result['why']))
        self.proposal['source_ids'] = ['uae-digital-accessibility-policy']
        self.role['status'] = 'partial'
        self.assertEqual(score_role(self.row, self.round)['rating'], 'partial')

    def test_unavailable_invalid_empty_and_missing_not_matches(self):
        for status, reason in [('unavailable','provider_error'), ('unavailable','invalid_response'), ('completed',None)]:
            self.role.update(status=status, reason=reason, proposals=[])
            self.assertEqual(score_role(self.row, self.round)['rating'], 'miss')
        self.assertEqual(score_role(self.row, None)['rating'], 'miss')

    def test_conflict_is_not_full_match(self):
        self.role['proposals'].append({'action_id':'start_workshop_now','fact_ids':['cf-1a'],'source_ids':['uae-digital-accessibility-policy']})
        result = score_role(self.row, self.round)
        self.assertEqual(result['rating'], 'partial')
        self.assertTrue(any('Starting now' in why for why in result['why']))

    def test_full_export_missing_rows_duplicate_and_render(self):
        report = score({'rounds':[self.round]})
        self.assertEqual(len(report['results']), 27)
        self.assertIn('| Stage | Role |', markdown(report))
        with self.assertRaises(ValueError):
            score({'rounds':[self.round,self.round]})
        with self.assertRaises(ValueError):
            score({'events':[]})

    def test_gaps_scenario_filter_and_sources(self):
        gaps=load_gaps()
        self.assertEqual(len(gaps['gaps']),3)
        for gap in gaps['gaps']:
            self.assertIn(gap['gap_type'], {'unclear responsibility','standards gap','technology gap','legislative gap','coordination problem','conflicting objectives'})
            self.assertEqual(len(load_gaps(gap['scenario_id'])['gaps']),1)
            self.assertTrue(gap['evidence_needed'])
            for ref in gap['uae_sources']:
                self.assertTrue(all(ref.get(k) for k in ('source_id','title','url','locator','says','does_not_say','scope')))
            for ref in gap['global_examples']:
                self.assertTrue(all(ref.get(k) for k in ('source_id','title','url','locator','addresses','scope','binding_status')))
        self.assertEqual(load_gaps('unknown')['gaps'],[])

if __name__ == '__main__':
    unittest.main()
