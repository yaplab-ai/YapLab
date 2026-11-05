"""Compare saved coordination rounds with a pre-authored, provisional rubric.

This is an evidence checklist, not a legal, educational or expert assessment.
"""
from __future__ import annotations
import json
from pathlib import Path

_PATH = Path(__file__).with_name('expected_outcomes.json')

def load_outcomes() -> dict:
    return json.loads(_PATH.read_text(encoding='utf-8'))

def _plan_check(row: dict, proposal: dict, plan: list[dict]) -> tuple[bool, str]:
    action = proposal.get('action_id')
    entries = [p for p in plan if p.get('action_id') == action]
    if len(entries) != 1:
        return False, 'Coordinator plan has no unique entry for the selected action.'
    item = entries[0]
    expected = row['expected_coordinator']
    if item.get('owner') != expected['owner']:
        return False, 'Coordinator owner does not match the role.'
    conditional = expected.get('conditional_action', {})
    if action == conditional.get('action_id'):
        handoffs = {(h.get('action_id'), h.get('owner')) for h in item.get('handoffs', [])}
        required = {(h['action_id'], h['owner']) for h in conditional['handoffs']}
        if not required <= handoffs:
            return False, 'Coordinator did not preserve both required handoffs.'
        selected = {p.get('action_id') for p in plan}
        missing = any(a not in selected for a, _ in required)
        status = conditional['status_if_any_handoff_missing' if missing else 'status_if_both_present']
    else:
        status = expected['status']
    if item.get('status') != status:
        return False, f'Coordinator status {item.get("status")!r}; expected {status!r}.'
    return True, 'Coordinator owner, status and applicable handoffs agree.'

def score_role(row: dict, round_data: dict | None) -> dict:
    key = {k: row[k] for k in ('scenario_id', 'stage', 'role')}
    result = {**key, 'expected': row, 'actual': None, 'actual_plan': [], 'rating': 'miss', 'why': []}
    if not round_data:
        result['why'] = ['No saved round for this stage.']
        return result
    role = next((r for r in round_data.get('roles', []) if r.get('role') == row['role']), None)
    if not role:
        result['why'] = ['Role result is absent from the saved round.']
        return result
    result['actual'] = role
    result['actual_plan'] = [p for p in round_data.get('plan', []) if p.get('owner') == row['role']]
    status = role.get('status')
    proposals = role.get('proposals', [])
    if status not in ('completed', 'partial'):
        result['why'] = [f'Role status is {status or "unknown"}; no supported outcome can be credited.',
                         f'Reason: {role.get("reason", "not recorded")}.']
        return result
    if not proposals:
        result['rating'] = 'partial' if role.get('reason') == 'insufficient_evidence' else 'miss'
        result['why'] = ['No action proposed; an abstention cannot demonstrate the expected response.']
        return result
    accepted = [p for p in proposals if p.get('action_id') in row['acceptable_action_ids']]
    if not accepted:
        result['why'] = ['No acceptable action was proposed.']
        return result
    expected_facts = set(row['expected_fact_ids_any'])
    expected_sources = set(row['expected_source_ids_any'])
    plan = round_data.get('plan', [])
    candidate_results = []
    for proposal in accepted:
        fact_ok = bool(expected_facts & set(proposal.get('fact_ids', [])))
        source_ok = bool(expected_sources & set(proposal.get('source_ids', [])))
        plan_ok, plan_reason = _plan_check(row, proposal, plan)
        candidate_results.append((sum((fact_ok, source_ok, plan_ok)), proposal, fact_ok, source_ok, plan_ok, plan_reason))
    _, best, fact_ok, source_ok, plan_ok, plan_reason = max(candidate_results, key=lambda x: x[0])
    notes = [f'Accepted action: {best.get("action_id")}.' , plan_reason]
    if not fact_ok:
        notes.append('The same proposal does not cite a rubric-relevant fact.')
    if not source_ok:
        offered = {s.get('source_id', s.get('id')) for s in role.get('evidence', []) if isinstance(s, dict)}
        if offered and not (expected_sources & offered):
            notes.append('No expected source appears in the recorded offered source context; source match cannot be demonstrated.')
        else:
            notes.append('The same proposal does not cite a rubric-expected source; relevance and applicability still require human review.')
    proposed_ids = {p.get('action_id') for p in proposals}
    # A proposal to confirm an option is not evidence that anyone confirmed it.
    conflict = row['scenario_id'] == 'caption-failure' and 'start_workshop_now' in proposed_ids
    if conflict:
        notes.append('Starting now is conditional on a usable option; the saved proposals alone do not prove human confirmation. Review any timing conflict.')
    if status == 'partial':
        notes.append('The role response was partially valid; discarded items cannot be assessed.')
    complete = fact_ok and source_ok and plan_ok and status == 'completed' and not conflict
    result.update(rating='match' if complete else 'partial', why=notes)
    return result

def extract_rounds(data: dict | list) -> list[dict]:
    if isinstance(data, list):
        return [r for item in data for r in extract_rounds(item)]
    if not isinstance(data, dict):
        raise ValueError('Expected a saved round, audit export, or list of either.')
    if isinstance(data.get('rounds'), list):
        return data['rounds']
    if 'scenario_id' in data and 'stage' in data and 'roles' in data:
        return [data]
    raise ValueError('No complete saved coordination rounds found; role-filtered audit events are insufficient.')

def score(data: dict | list, rubric: dict | None = None) -> dict:
    rubric = rubric or load_outcomes()
    rounds = extract_rounds(data)
    index = {}
    for rnd in rounds:
        key = (rnd.get('scenario_id'), rnd.get('stage'))
        if key in index:
            raise ValueError(f'Multiple rounds for {key}; select one per scenario and stage explicitly.')
        index[key] = rnd
    return {'label': rubric['label'], 'authorship_note': rubric['authorship_note'],
            'limitations': ['A checklist comparison of saved synthetic exercise outputs; neither legal advice nor proof of educational benefit.',
                            'A matching citation is an ID-level relevance check, not proof of source applicability or entailment.'],
            'results': [score_role(row, index.get((row['scenario_id'], row['stage']))) for row in rubric['entries']]}

def markdown(report: dict) -> str:
    lines = ['# Expected and actual outcomes', '', report['label'], '', report['authorship_note'], '']
    for scenario in dict.fromkeys(r['scenario_id'] for r in report['results']):
        lines += [f'## {scenario}', '', '| Stage | Role | Expected action(s) | Actual action(s) / status | Result | Why |', '|---|---|---|---|---|---|']
        for result in (r for r in report['results'] if r['scenario_id'] == scenario):
            actual = result['actual'] or {}
            actions = ', '.join(p.get('action_id', '?') for p in actual.get('proposals', [])) or 'none'
            cells = [str(result['stage']), result['role'], ', '.join(result['expected']['acceptable_action_ids']), f"{actions} / {actual.get('status', 'missing')}", result['rating'], ' '.join(result['why'])]
            lines.append('| ' + ' | '.join(str(c).replace('|', '\\|').replace('\n', ' ') for c in cells) + ' |')
        lines.append('')
    lines += ['Limitations: ' + ' '.join(report['limitations']), '']
    return '\n'.join(lines)
