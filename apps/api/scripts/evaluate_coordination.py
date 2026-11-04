#!/usr/bin/env python3
"""Plan or explicitly run a bounded synthetic coordination evaluation."""
from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from frontrow.llm.base import llm_call_context
from frontrow.llm.openai_client import OpenAIClient
from frontrow.policy.coordination import PROTOCOL_VERSION, ROLES, coordinate, prepare_role_requests
from frontrow.policy.evidence import load_corpus
from frontrow.policy.scenarios import ExerciseStore, _SCENARIOS

MODEL = 'nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B'
SCENARIOS = ('transcript-disclosure', 'caption-failure', 'feedback-as-grade')
MAX_CALLS = 27
MAX_OUTPUT = 400
INPUT_PRICE = 0.06
OUTPUT_PRICE = 0.24


def snapshots():
    """Obtain role-filtered released facts from the same store used by the app."""
    if {s['id'] for s in _SCENARIOS} != set(SCENARIOS) or any(len(s['stages']) != 3 for s in _SCENARIOS):
        raise ValueError('The synthetic evaluation requires exactly the three expected three-stage scenarios')
    store = ExerciseStore()
    for scenario in SCENARIOS:
        created = store.create(scenario, 'teacher')
        exercise_id = created['exercise_id']
        for stage in (1, 2, 3):
            if stage > 1:
                store.advance(exercise_id, 'teacher', stage - 1)
            reserved = store.reserve_coordination(exercise_id, stage, 'general')
            yield {key: reserved[key] for key in ('scenario_id', 'stage', 'role_views')}
            store.release_coordination(exercise_id, reserved['round_id'])


def prepare():
    corpus = load_corpus()
    states = list(snapshots())
    calls = []
    for state in states:
        for request in prepare_role_requests(corpus, state, 'general'):
            size = len(request['system'].encode('utf-8')) + len(request['user'].encode('utf-8'))
            calls.append({'scenario_id': state['scenario_id'], 'stage': state['stage'],
                          'role': request['role'], 'input_utf8_bytes': size,
                          'prompt_sha256': request['prompt_sha256'], 'prompt_attempted': False,
                          'evidence': request['evidence']})
    if len(states) != 9 or len(calls) != MAX_CALLS or any(not call['input_utf8_bytes'] for call in calls):
        raise ValueError('Unexpected evaluation shape')
    # A deliberately generous planning proxy, not a tokenizer result or a guaranteed bound.
    input_envelope = sum(2 * call['input_utf8_bytes'] + 1024 for call in calls)
    output_envelope = MAX_CALLS * MAX_OUTPUT
    cost = (input_envelope * INPUT_PRICE + output_envelope * OUTPUT_PRICE) / 1_000_000
    plan = {'mode': 'dry_run', 'network_calls_made': 0, 'institution': 'general',
            'protocol_version': PROTOCOL_VERSION, 'corpus_version': corpus.version,
            'scenario_count': 3, 'stages_per_scenario': 3, 'roles_per_snapshot': len(ROLES),
            'planned_provider_calls': len(calls), 'calls': calls,
            'prompt_utf8_bytes_total': sum(item['input_utf8_bytes'] for item in calls),
            'planning_input_tokens_proxy': input_envelope, 'max_output_tokens_per_request': MAX_OUTPUT,
            'max_total_output_tokens': output_envelope,
            'pricing': {'provider': 'nebius', 'model': MODEL, 'currency': 'USD',
                        'input_per_million': INPUT_PRICE, 'output_per_million': OUTPUT_PRICE,
                        'as_of': '2026-11-04', 'estimated_envelope_usd': round(cost, 8),
                        'planned_budget_usd': 0.10,
                        'note': 'Input proxy is 2 tokens per prompt UTF-8 byte plus 1024 per call; not a tokenizer count, enforced input cap, or billing guarantee. Pricing and protocol overhead may change.'},
            'structural_validation': 'not_run', 'human_semantic_quality': 'unreviewed'}
    return corpus, states, plan


class LimitedNebius(OpenAIClient):
    """Limit attempted calls before invoking the existing no-retry, 400-token adapter."""
    def __init__(self):
        super().__init__(provider='nebius')
        self.attempts = 0

    async def complete(self, system, user, *, model, timeout):
        if model != MODEL or self.provider_name != 'nebius' or self.attempts >= MAX_CALLS:
            raise ValueError('Evaluation call limit or model violated')
        self.attempts += 1
        return await super().complete(system, user, model=model, timeout=timeout)


def bounded_usage(event):
    if event.get('kind') != 'request':
        return None
    usage = event.get('usage')
    if not isinstance(usage, dict):
        usage = {}
    def number(value):
        return value if type(value) is int and 0 <= value <= 1_000_000_000 else None
    return {'role': event.get('role') if event.get('role') in {'policy_coordination_' + r for r in ROLES} else None,
            'outcome': event.get('outcome') if event.get('outcome') in ('success', 'error', 'cancelled') else 'unknown',
            'input_tokens': number(usage.get('prompt_tokens')),
            'output_tokens': number(usage.get('completion_tokens'))}


def summarize(result):
    roles = []
    for role in result['roles']:
        roles.append({'role': role['role'], 'status': role['status'],
                      'reason': role.get('reason'),
                      'prompt_sha256': role['prompt_sha256'],
                      'prompt_attempted': role['prompt_attempted'],
                      'evidence': [{k: evidence[k] for k in ('id', 'title', 'url', 'authority',
                                   'jurisdiction', 'document_type', 'scope', 'summary', 'limitations',
                                   'institution', 'sha256')} for evidence in role['evidence']],
                      'proposals': [{k: p[k] for k in ('action_id', 'fact_ids', 'source_ids')}
                                    for p in role['proposals']],
                      'question_ids': [q['question_id'] for q in role['questions']]})
    return {'scenario_id': result['scenario_id'], 'stage': result['stage'],
            'institution': result['institution'], 'protocol_version': result['protocol_version'],
            'corpus_version': result['corpus_version'],
            'model': {k: result['model'][k] for k in ('provider', 'model')},
            'roles': roles,
            'structural_validation': 'pass' if all(r['status'] == 'completed' for r in roles) else 'fail',
            'human_semantic_quality': 'unreviewed',
            'plan': [{k: p[k] for k in ('action_id', 'owner', 'status', 'depends_on')} for p in result['plan']],
            'unresolved_count': len(result['unresolved'])}


async def run_live(corpus, states, plan, approval_reference):
    client = LimitedNebius()
    records, usage = [], []
    def observe(event):
        item = bounded_usage(event)
        if item is not None and len(usage) < MAX_CALLS:
            usage.append(item)
    try:
        for state in states:
            with llm_call_context('fast', 'evaluation', observer=observe):
                result = await coordinate(corpus, state, client, MODEL, institution='general', mode='model_assisted')
            records.append(summarize(result))
    finally:
        await client.aclose()
    missing = sum(item['input_tokens'] is None or item['output_tokens'] is None for item in usage)
    return {'mode': 'live_provider_evaluation', 'approval_reference': approval_reference,
            'provider': 'nebius', 'model': {'provider': 'nebius', 'model': MODEL}, 'institution': 'general',
            'protocol_version': PROTOCOL_VERSION, 'corpus_version': corpus.version,
            'provider_call_attempts': client.attempts, 'usage': usage,
            'usage_missing_calls': missing + max(0, client.attempts - len(usage)),
            'max_output_tokens_per_request': MAX_OUTPUT, 'planning': plan['pricing'],
            'structural_validation': 'pass' if all(r['structural_validation'] == 'pass' for r in records) else 'fail',
            'human_semantic_quality': 'unreviewed', 'snapshots': records}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute-live', action='store_true', help='perform bounded, billable provider calls')
    parser.add_argument('--approval-reference', help='identifier of separate explicit approval, recorded verbatim')
    parser.add_argument('--provider', choices=['nebius'], help='explicitly choose the live evaluation provider')
    parser.add_argument('--model', default=MODEL, choices=[MODEL])
    parser.add_argument('--output', type=Path, help='new output file; live runs require this option')
    args = parser.parse_args()
    if args.execute_live:
        if args.provider != 'nebius':
            parser.error('--execute-live requires explicit --provider nebius')
        if not args.approval_reference or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}', args.approval_reference):
            parser.error('--execute-live requires a nonempty approval reference identifier (letters, digits, . _ : / -)')
        if not args.output:
            parser.error('--execute-live requires a new --output file')
        if not os.environ.get('NEBIUS_API_KEY'):
            parser.error('NEBIUS_API_KEY must be present in the environment')
        if importlib.util.find_spec('openai') is None:
            parser.error('the optional openai SDK must be installed')
    elif args.approval_reference:
        parser.error('--approval-reference is only accepted with --execute-live')
    corpus, states, plan = prepare()
    if args.execute_live and plan['pricing']['estimated_envelope_usd'] > 0.10:
        parser.error('planning estimate exceeds the $0.10 envelope')
    if args.output:
        # Exclusive creation happens before any provider call; never overwrite a file.
        try:
            with args.output.open('x', encoding='utf-8') as out:
                result = asyncio.run(run_live(corpus, states, plan, args.approval_reference)) if args.execute_live else plan
                json.dump(result, out, ensure_ascii=False, indent=2)
                out.write('\n')
        except FileExistsError:
            parser.error('output already exists')
        print(f"{'Live result' if args.execute_live else 'Dry-run plan'} saved: {args.output}")
    else:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
