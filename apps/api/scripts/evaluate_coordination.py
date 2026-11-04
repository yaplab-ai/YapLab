#!/usr/bin/env python3
"""Plan or explicitly run a bounded synthetic coordination evaluation."""
from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import math
from collections import Counter
from decimal import Decimal
import os
import re
import stat
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from frontrow.llm.base import llm_call_context
from frontrow.llm.openai_client import OpenAIClient
from frontrow.policy.coordination import PROTOCOL_VERSION, ROLES, coordinate, prepare_role_requests
from frontrow.policy.diagnostics import VALIDATION_ISSUES
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
            'structural_validation': 'not_run', 'validation_issue_counts': {},
            'human_semantic_quality': 'unreviewed'}
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


FINISH_REASONS = frozenset(('stop', 'length', 'content_filter', 'tool_calls', 'function_call'))
ERROR_TYPES = frozenset(('APIConnectionError', 'APITimeoutError', 'RateLimitError', 'AuthenticationError',
                         'PermissionDeniedError', 'BadRequestError', 'InternalServerError', 'APIStatusError',
                         'APIError', 'TimeoutError', 'CancelledError'))
ROLE_REASONS = frozenset(('insufficient_evidence', 'timeout', 'invalid_response', 'validation_error',
                          'provider_error', 'overall_timeout'))


def _allow(value, values):
    return value if isinstance(value, str) and value in values else None


def bounded_usage(event, *, scenario_id=None, stage=None):
    if not isinstance(event, dict) or event.get('kind') != 'request':
        return None
    usage = event.get('usage')
    if not isinstance(usage, dict):
        usage = {}
    def number(value):
        return value if type(value) is int and 0 <= value <= 1_000_000_000 else None
    latency = event.get('latency_seconds')
    latency_ms = (round(latency * 1000, 3) if type(latency) in (int, float)
                  and 0 <= latency <= 60 and math.isfinite(latency) else None)
    return {'scenario_id': scenario_id if scenario_id in SCENARIOS else None,
            'stage': stage if type(stage) is int and stage in (1, 2, 3) else None,
            'role': _allow(event.get('role'), {'policy_coordination_' + r for r in ROLES}),
            'outcome': _allow(event.get('outcome'), {'success', 'error', 'cancelled'}) or 'unknown',
            'finish_reason': _allow(event.get('finish_reason'), FINISH_REASONS),
            'error_type': _allow(event.get('error_type'), ERROR_TYPES),
            'latency_ms': latency_ms,
            'input_tokens': number(usage.get('prompt_tokens')),
            'output_tokens': number(usage.get('completion_tokens'))}


def summarize(result):
    roles = []
    for role in result['roles']:
        roles.append({'role': _allow(role['role'], ROLES),
                      'status': _allow(role['status'], ('completed', 'partial', 'unavailable')) or 'unavailable',
                      'reason': _allow(role.get('reason'), ROLE_REASONS),
                      'prompt_sha256': role['prompt_sha256'],
                      'prompt_attempted': role['prompt_attempted'] is True,
                      'evidence': [{**{k: evidence[k] for k in ('id', 'title', 'url', 'authority',
                                   'jurisdiction', 'document_type', 'scope', 'summary', 'limitations',
                                   'institution', 'sha256')},
                                   **{k: evidence[k] for k in ('source_locator', 'verification') if k in evidence}}
                                   for evidence in role['evidence']],
                      'proposals': [{k: p[k] for k in ('action_id', 'fact_ids', 'source_ids')}
                                    for p in role['proposals']],
                      'question_ids': [q['question_id'] for q in role['questions']]})
    for item, role in zip(roles, result['roles']):
        issue = _allow(role.get('validation_issue'), VALIDATION_ISSUES)
        if item['reason'] == 'invalid_response' and issue is not None:
            item['validation_issue'] = issue
    return {'scenario_id': result['scenario_id'], 'stage': result['stage'],
            'institution': result['institution'], 'protocol_version': result['protocol_version'],
            'corpus_version': result['corpus_version'],
            'model': {k: result['model'][k] for k in ('provider', 'model')},
            'roles': roles,
            'structural_validation': 'pass' if all(r['status'] == 'completed' for r in roles) else 'fail',
            'human_semantic_quality': 'unreviewed',
            'plan': [{'action_id': p['action_id'], 'owner': _allow(p['owner'], ROLES),
                      'status': _allow(p['status'], ('conflicting_proposals', 'missing_prerequisites',
                                                     'awaiting_human_confirmation')),
                      'depends_on': p['depends_on']} for p in result['plan']],
            'unresolved_count': len(result['unresolved'])}


def known_usage_cost(usage, plan):
    """Price each reported token count, including partial usage, at the plan's list prices."""
    pricing = plan['pricing']
    input_price = Decimal(str(pricing.get('input_per_million', INPUT_PRICE)))
    output_price = Decimal(str(pricing.get('output_per_million', OUTPUT_PRICE)))
    return sum((Decimal(item['input_tokens'] or 0) * input_price +
                Decimal(item['output_tokens'] or 0) * output_price) / Decimal(1_000_000)
               for item in usage)


def evaluation_progress(corpus, plan, approval_reference, client, records, usage, *,
                        status, stop_reason=None, in_flight=None):
    roles = [role for record in records for role in record['roles']]
    missing = sum(item['input_tokens'] is None or item['output_tokens'] is None for item in usage)
    missing += max(0, client.attempts - len(usage))
    cost = known_usage_cost(usage, plan)
    invalid = [role for role in roles if role['reason'] == 'invalid_response']
    counts = Counter(role['validation_issue'] for role in invalid if 'validation_issue' in role)
    complete = status == 'completed'
    return {'mode': 'live_provider_evaluation', 'approval_reference': approval_reference,
            'provider': 'nebius', 'model': {'provider': 'nebius', 'model': MODEL}, 'institution': 'general',
            'protocol_version': PROTOCOL_VERSION, 'corpus_version': corpus.version,
            'run_status': status, 'stop_reason': stop_reason, 'in_flight_snapshot': in_flight,
            'planned_snapshots': 9, 'completed_snapshots': len(records),
            'planned_provider_calls': MAX_CALLS, 'provider_call_attempts': client.attempts,
            'provider_success_events': sum(item['outcome'] == 'success' for item in usage),
            'provider_failure_events': sum(item['outcome'] in ('error', 'cancelled') for item in usage),
            'structurally_completed_roles': sum(role['status'] == 'completed' for role in roles),
            'partially_completed_roles': sum(role['status'] == 'partial' for role in roles),
            'structurally_failed_roles': sum(role['status'] != 'completed' for role in roles),
            'usage': list(usage), 'usage_missing_calls': missing,
            'reported_usage_cost': {'known_cost_usd': float(cost),
                'complete_cost_usd': float(cost) if complete and missing == 0 and len(usage) == client.attempts and in_flight is None else None,
                'invoice_verified': False, 'pricing_as_of': plan['pricing'].get('as_of'),
                'note': 'List-price estimate from reported usage only; actual invoice and pending/failed charges are unverified.'},
            'max_output_tokens_per_request': MAX_OUTPUT, 'planning': plan['pricing'],
            'structural_validation': ('not_complete' if not complete else
                                      'pass' if all(r['structural_validation'] == 'pass' for r in records) else 'fail'),
            'validation_issue_counts': dict(sorted(counts.items())),
            'invalid_response_without_known_issue': len(invalid) - sum(counts.values()),
            'human_semantic_quality': 'unreviewed', 'snapshots': list(records)}


class CheckpointFailure(RuntimeError):
    """The local checkpoint failed; no further provider calls are allowed."""


async def run_live(corpus, states, plan, approval_reference, *, checkpoint=None):
    client = LimitedNebius()
    records, usage = [], []
    status, stop_reason, in_flight = 'in_progress', None, None
    def save():
        result = evaluation_progress(corpus, plan, approval_reference, client, records, usage,
                                     status=status, stop_reason=stop_reason, in_flight=in_flight)
        if checkpoint is not None:
            try:
                checkpoint(result)
            except Exception:
                # Keep a sanitized record even if the output filesystem is unavailable.
                fallback = {**result, 'run_status': 'stopped', 'stop_reason': 'checkpoint_failed'}
                print('Checkpoint failed; sanitized recovery record follows:', file=sys.stderr)
                print(json.dumps(fallback, ensure_ascii=False), file=sys.stderr)
                raise CheckpointFailure('Checkpoint failed') from None
        return result
    try:
        save()
        for state in states:
            in_flight = {'scenario_id': state['scenario_id'], 'stage': state['stage']}
            save()  # An interruption after this point leaves charges for this snapshot unknown.
            before_attempts, before_events = client.attempts, len(usage)
            def observe(event, *, scenario_id=state['scenario_id'], stage=state['stage']):
                item = bounded_usage(event, scenario_id=scenario_id, stage=stage)
                if item is not None and len(usage) < MAX_CALLS:
                    usage.append(item)
            try:
                with llm_call_context('fast', 'evaluation', observer=observe):
                    result = await coordinate(corpus, state, client, MODEL, institution='general', mode='model_assisted')
                records.append(summarize(result))
            except Exception:
                # Do not persist exception messages, which may contain provider content.
                status, stop_reason, in_flight = 'stopped', 'internal_error', None
                save()
                break
            in_flight = None
            new_usage = usage[before_events:]
            new_attempts = client.attempts - before_attempts
            reasons = {role['reason'] for role in records[-1]['roles']}
            if any(item['output_tokens'] is not None and item['output_tokens'] > MAX_OUTPUT for item in new_usage):
                status, stop_reason = 'stopped', 'reported_output_limit_exceeded'
            elif known_usage_cost(usage, plan) >= Decimal(str(plan['pricing']['planned_budget_usd'])):
                status, stop_reason = 'stopped', 'reported_cost_budget_reached'
            elif reasons & {'provider_error', 'timeout', 'overall_timeout', 'validation_error'} or any(
                    item['outcome'] in ('error', 'cancelled', 'unknown') for item in new_usage):
                status, stop_reason = 'stopped', 'provider_or_internal_failure'
            elif len(new_usage) != new_attempts or any(item['input_tokens'] is None or item['output_tokens'] is None
                                                       for item in new_usage):
                status, stop_reason = 'stopped', 'usage_missing'
            save()
            if status == 'stopped':
                break
        else:
            status = 'completed' if len(records) == 9 else 'stopped'
            if status == 'stopped':
                stop_reason = 'incomplete_snapshot_set'
        return save()
    finally:
        await client.aclose()


def _reject_output_symlinks(path):
    absolute = Path(path).absolute()
    if any(part.is_symlink() for part in (absolute, *absolute.parents)):
        raise ValueError('output path contains a symlink')


def reserve_output(path):
    """Reserve a previously absent destination before starting provider calls."""
    _reject_output_symlinks(path)
    # Exclusive creation rejects existing regular files and final-component symlinks.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    os.close(fd)


def atomic_checkpoint(path, result):
    """Fsync a new same-directory file, replace the reservation, and sync its directory."""
    path = Path(path)
    _reject_output_symlinks(path)
    temp_path = None
    directory_fd = None
    try:
        fd, temp_name = tempfile.mkstemp(prefix='.' + path.name + '.', suffix='.tmp', dir=path.parent)
        temp_path = Path(temp_name)
        try:
            stream = os.fdopen(fd, 'w', encoding='utf-8')
        except BaseException:
            os.close(fd)
            raise
        with stream:
            json.dump(result, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        # A failure before replace leaves the preceding checkpoint intact.
        directory_fd = os.open(path.parent, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0))
        _reject_output_symlinks(path)
        if not stat.S_ISREG(path.stat(follow_symlinks=False).st_mode):
            raise ValueError('reserved output is not a regular file')
        os.replace(temp_path, path)
        temp_path = None
        # If this fails, replacement occurred but directory durability is uncertain.
        os.fsync(directory_fd)
    finally:
        if directory_fd is not None:
            os.close(directory_fd)
        if temp_path is not None:
            try:
                temp_path.unlink()
            except FileNotFoundError:
                pass


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
        try:
            reserve_output(args.output)
        except FileExistsError:
            parser.error('output already exists')
        except ValueError:
            parser.error('output path contains a symlink')
        def checkpoint(result):
            atomic_checkpoint(args.output, result)
        if args.execute_live:
            try:
                result = asyncio.run(run_live(corpus, states, plan, args.approval_reference, checkpoint=checkpoint))
            except CheckpointFailure:
                return 1
            print(f"Live result saved: {args.output}; run_status={result['run_status']}; "
                  f"structural_validation={result['structural_validation']}")
            if result['run_status'] != 'completed':
                return 1
            if result['structural_validation'] != 'pass':
                return 2
        else:
            checkpoint(plan)
            print(f'Dry-run plan saved: {args.output}')
    else:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
