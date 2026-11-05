#!/usr/bin/env python3
"""Run one bounded synthetic Policy Lab pass through its HTTP API.

Default invocation is a network-free plan. The live server must already be
configured by the operator for the authorized Nebius model, 400 output tokens,
no fallback and no retries. This driver neither reads credentials nor launches it.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[3]
MODEL = 'nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B'
CORPUS_VERSION = '2026-11-05.5'
PROTOCOL = '4'
MAX_CALLS = 27
SCENARIOS = ('transcript-disclosure', 'caption-failure', 'feedback-as-grade')
ROLES = ('teacher', 'privacy', 'accessibility')
DECISIONS = {
    'transcript-disclosure': ('td-1a', 'Synthetic facilitator decision: ask the course team to review the shared transcript and agree human-owned next steps.'),
    'caption-failure': ('cf-1a', 'Synthetic facilitator decision: ask the teaching team to consider a usable alternative and confirm it with the attendee.'),
    'feedback-as-grade': ('fg-1a', 'Synthetic facilitator decision: ask the teaching team to review the practice feedback and prepare a clear explanation.'),
}


def plan():
    return {'mode': 'dry_run', 'network_requests': 0, 'provider_calls': 0,
            'scenarios': list(SCENARIOS), 'stages_per_scenario': 3, 'roles_per_stage': 3,
            'maximum_provider_attempts': MAX_CALLS, 'model': MODEL,
            'protocol_version': PROTOCOL, 'expected_corpus_version': CORPUS_VERSION,
            'instructions': 'Explicit --execute-live, --approval-reference, --api-url and a new --output directory are required.'}


def loopback_url(url):
    parts = urlsplit(url)
    if (parts.scheme not in ('http', 'https') or not parts.hostname or parts.username is not None
            or parts.password is not None or parts.path not in ('', '/') or parts.query or parts.fragment):
        raise ValueError('API URL must be a loopback HTTP(S) origin without credentials, path, query or fragment')
    try:
        port = parts.port
    except ValueError:
        raise ValueError('Invalid API port') from None
    host = parts.hostname
    try:
        addresses = [ipaddress.ip_address(host)]
    except ValueError:
        if host.lower() != 'localhost':
            raise ValueError('API URL must use a loopback address') from None
        addresses = [ipaddress.ip_address(item[4][0]) for item in socket.getaddrinfo(host, port or 80, type=socket.SOCK_STREAM)]
    if not addresses or not all(address.is_loopback for address in addresses):
        raise ValueError('API URL must resolve only to loopback addresses')
    return url.rstrip('/')


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class HTTPTransport:
    def __init__(self, origin):
        self.origin = loopback_url(origin)
        self.opener = build_opener(ProxyHandler({}), NoRedirect())

    def request(self, method, path, body=None):
        data = None if body is None else json.dumps(body, ensure_ascii=False).encode('utf-8')
        request = Request(self.origin + path, data=data, method=method,
                          headers={'Accept': 'application/json, text/html', **({'Content-Type': 'application/json'} if data else {})})
        with self.opener.open(request, timeout=180) as response:
            return response.read()


def code_provenance():
    commit = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    dirty = bool(subprocess.run(['git', 'status', '--porcelain'], cwd=ROOT, check=True, capture_output=True, text=True).stdout)
    paths = sorted(path for path in (ROOT / 'apps/api/frontrow').rglob('*')
                   if path.is_file() and path.suffix in ('.py', '.json') and '__pycache__' not in path.parts)
    paths.append(Path(__file__).resolve())
    digest = hashlib.sha256()
    for path in paths:
        name = str(path.relative_to(ROOT)).encode('utf-8')
        data = path.read_bytes()
        digest.update(len(name).to_bytes(8, 'big')); digest.update(name)
        digest.update(len(data).to_bytes(8, 'big')); digest.update(data)
    return {'source_commit': commit, 'working_tree_dirty': dirty, 'code_sha256': digest.hexdigest(),
            'code_hash_scope': 'apps/api/frontrow .py and .json files and this driver',
            'note': 'Checkout fingerprint only; does not independently attest the running server.'}


def atomic_write(path, data):
    temp = path.with_name('.' + path.name + '.tmp')
    with temp.open('xb') as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp, path)


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n').encode('utf-8')


def decode(raw):
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError('Expected JSON object')
    return value


def estimate(rows, uncertain, run_completed=False):
    observed_input = observed_output = missing = 0
    for item in rows:
        usage = item.get('usage')
        if (not isinstance(usage, dict) or type(usage.get('prompt_tokens')) is not int
                or type(usage.get('completion_tokens')) is not int
                or usage['prompt_tokens'] < 0 or usage['completion_tokens'] < 0):
            if item.get('prompt_attempted'):
                missing += 1
            continue
        observed_input += usage['prompt_tokens']; observed_output += usage['completion_tokens']
    amount = (Decimal(observed_input) * Decimal('0.06') + Decimal(observed_output) * Decimal('0.24')) / Decimal(1_000_000)
    return {'currency': 'USD', 'input_tokens_observed': observed_input, 'output_tokens_observed': observed_output,
            'input_per_million_usd': 0.06, 'output_per_million_usd': 0.24,
            'estimated_observed_usd': str(amount), 'missing_usage_attempts': missing,
            'complete': run_completed and not missing and not uncertain, 'invoice': False, 'invoice_verified': False,
            'note': 'List-price estimate for reported usage only; not an invoice or a complete cost when usage is missing or an outcome is unknown.'}


class Driver:
    def __init__(self, transport, output, approval_reference, provenance):
        self.transport = transport
        self.output = Path(output)
        self.approval = approval_reference
        self.provenance = provenance
        self.manifest = None

    def save_manifest(self):
        self.manifest['cost_estimate'] = estimate(self.manifest['role_results'], self.manifest['uncertain_outcome'],
                                                   self.manifest['run_status'] == 'completed')
        self.manifest['updated_at'] = datetime.now(timezone.utc).isoformat()
        atomic_write(self.output / 'manifest.json', json_bytes(self.manifest))

    def save_file(self, filename, data):
        atomic_write(self.output / filename, data)
        self.manifest['files'][filename] = hashlib.sha256(data).hexdigest()
        self.save_manifest()

    def request(self, method, path, body=None):
        return self.transport.request(method, path, body)

    def run(self):
        if not isinstance(self.approval, str) or not self.approval.strip() or len(self.approval) > 500:
            raise ValueError('A nonempty approval reference is required')
        self.output.mkdir(parents=False, exist_ok=False)
        self.manifest = {'mode': 'model_assisted', 'run_status': 'running', 'approval_reference': self.approval.strip(),
                         **self.provenance, 'model': MODEL, 'provider': 'nebius', 'protocol_version': PROTOCOL,
                         'corpus_version': CORPUS_VERSION, 'request_bound': MAX_CALLS, 'reserved_provider_attempts': 0,
                         'uncertain_outcome': False, 'role_results': [], 'completed_stages': [], 'files': {},
                         'limitations': ['Synthetic facilitator decisions; no educational outcomes measured.',
                                         'Status endpoint reports model, provider and protocol; it does not independently attest running server code.',
                                         'A reservation is an upper bound on possible provider attempts, not a claim they occurred.']}
        self.save_manifest()
        phase = 'preflight'
        try:
            status = decode(self.request('GET', '/policy/coordination/status'))
            if (status.get('enabled') is not True or status.get('review_mode') != 'model_assisted'
                    or status.get('model') != MODEL or status.get('provider') != 'nebius'
                    or status.get('protocol_version') != PROTOCOL):
                raise ValueError('Model-assisted coordination preflight failed')
            sources = decode(self.request('GET', '/policy/sources?institution=general'))
            if sources.get('version') != CORPUS_VERSION:
                raise ValueError('Corpus version preflight failed')
            for scenario in SCENARIOS:
                phase = 'create'
                view = decode(self.request('POST', '/policy/exercises?role=teacher', {'scenario_id': scenario}))
                exercise = view['exercise_id']
                if (not isinstance(exercise, str) or not exercise or not all(c.isalnum() or c in '-_' for c in exercise)
                        or view.get('scenario_id') != scenario or view.get('current_stage') != 1):
                    raise ValueError('Invalid exercise response')
                base = '/policy/exercises/' + exercise
                for stage in (1, 2, 3):
                    if stage > 1:
                        phase = 'advance'
                        view = decode(self.request('POST', base + '/advance?role=teacher', {'expected_stage': stage - 1}))
                    if view.get('scenario_id') != scenario or view.get('current_stage') != stage:
                        raise ValueError('Unexpected exercise stage')
                    fact_id, decision = DECISIONS[scenario]
                    visible = {fact['id'] for part in view['released_stages'] for fact in part['facts']}
                    if fact_id not in visible:
                        raise ValueError('Facilitator fact is not visible')
                    if self.manifest['reserved_provider_attempts'] + 3 > MAX_CALLS:
                        raise ValueError('Provider attempt reservation exceeds limit')
                    phase = 'coordinate'
                    self.manifest.update({'reserved_provider_attempts': self.manifest['reserved_provider_attempts'] + 3,
                                          'in_flight': {'scenario_id': scenario, 'stage': stage, 'reserved': 3},
                                          'uncertain_outcome': True})
                    self.save_manifest()
                    raw = self.request('POST', base + '/coordinate', {'expected_stage': stage, 'institution': 'general'})
                    self.save_file(f'{scenario}-stage-{stage}-round.json', raw)
                    round_result = decode(raw)
                    if (round_result.get('scenario_id') != scenario or round_result.get('stage') != stage
                            or round_result.get('protocol_version') != PROTOCOL or round_result.get('corpus_version') != CORPUS_VERSION
                            or round_result.get('review_mode') != 'model_assisted'
                            or round_result.get('model') != {'provider': 'nebius', 'model': MODEL}):
                        raise ValueError('Coordination provenance mismatch')
                    roles = round_result.get('roles')
                    if not isinstance(roles, list) or len(roles) != 3 or {item.get('role') for item in roles} != set(ROLES):
                        raise ValueError('Invalid coordination role results')
                    for item in roles:
                        self.manifest['role_results'].append({'scenario_id': scenario, 'stage': stage,
                            **{key: item.get(key) for key in ('role', 'status', 'reason', 'prompt_attempted', 'prompt_sha256',
                                'provider_status', 'usage', 'latency_ms', 'validation_issue')},
                            'rationale_rejections': [proposal.get('rationale_issue') for proposal in item.get('proposals', [])
                                                      if proposal.get('rationale_rejected')]})
                    self.manifest['uncertain_outcome'] = False
                    self.manifest.pop('in_flight', None)
                    self.save_manifest()
                    phase = 'decision'
                    self.request('POST', base + '/decision', {'role': 'teacher', 'decision': decision,
                                                             'source_ids': [fact_id], 'expected_stage': stage})
                    phase = 'export'
                    timeline_raw = self.request('GET', base + '/timeline')
                    timeline = decode(timeline_raw)
                    if timeline.get('scenario_id') != scenario or timeline.get('current_stage') != stage:
                        raise ValueError('Timeline does not match current stage')
                    self.save_file(f'{scenario}-stage-{stage}.json', timeline_raw)
                    html = self.request('GET', base + '/timeline.html')
                    self.save_file(f'{scenario}-stage-{stage}.html', html)
                    if stage == 3:
                        self.save_file(f'{scenario}.json', timeline_raw)
                        self.save_file(f'{scenario}.html', html)
                    self.manifest['completed_stages'].append({'scenario_id': scenario, 'stage': stage})
                    self.save_manifest()
            self.manifest['run_status'] = 'completed'
            self.save_manifest()
            return self.manifest
        except Exception as exc:
            self.manifest.update({'run_status': 'stopped', 'stopped_phase': phase,
                                  'failure_category': type(exc).__name__})
            if isinstance(exc, HTTPError):
                self.manifest['http_status'] = exc.code
            self.save_manifest()
            raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute-live', action='store_true')
    parser.add_argument('--approval-reference')
    parser.add_argument('--api-url')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    if not args.execute_live:
        print(json.dumps(plan(), indent=2))
        return 0
    if not args.approval_reference or not args.api_url or args.output is None:
        parser.error('--execute-live requires --approval-reference, --api-url and --output')
    try:
        transport = HTTPTransport(args.api_url)
        result = Driver(transport, args.output, args.approval_reference, code_provenance()).run()
    except Exception as exc:
        print(f'Evaluation stopped ({type(exc).__name__}); inspect the checkpoint if created. No retry was attempted.', file=sys.stderr)
        return 1
    print(f"Evaluation {result['run_status']}; reserved provider attempts: {result['reserved_provider_attempts']}/{MAX_CALLS}; evidence: {args.output}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
