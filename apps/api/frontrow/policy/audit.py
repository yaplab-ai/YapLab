"""Portable synthetic exercise audit and read-only recorded-run validation."""
from __future__ import annotations

import hashlib
import html
import json
from datetime import datetime


def digest(value: dict) -> str:
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()


def seal(value: dict) -> dict:
    return {**value, 'sha256': digest(value)}


def validate_recording(value: object) -> dict:
    """Check integrity and provenance without changing saved model outputs."""
    if not isinstance(value, dict) or value.get('version') != '1':
        raise ValueError('Unsupported recording')
    supplied = value.get('sha256')
    payload = {key: item for key, item in value.items() if key != 'sha256'}
    if not isinstance(supplied, str) or supplied != digest(payload):
        raise ValueError('Recording hash mismatch')
    rounds = value.get('rounds')
    events = value.get('events')
    if not isinstance(rounds, list) or not rounds or not isinstance(events, list):
        raise ValueError('Recording has no saved rounds')
    for item in rounds:
        if (not isinstance(item, dict) or item.get('review_mode') != 'model_assisted'
                or item.get('protocol_version') != '4' or item.get('model', {}).get('provider') != 'nebius'
                or item.get('model', {}).get('model') != 'nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B'
                or item.get('scenario_id') != value.get('scenario_id')):
            raise ValueError('Recording is not a protocol 4 Nebius live run')
    stage = value.get('current_stage')
    if type(stage) is not int or not 1 <= stage <= 3:
        raise ValueError('Invalid recorded stage')
    first = next((event for event in events if isinstance(event, dict) and event.get('type') == 'stage_release'), {})
    date = first.get('at', '')
    try:
        date = datetime.fromisoformat(date.replace('Z', '+00:00')).date().isoformat()
    except (ValueError, AttributeError):
        raise ValueError('Recording date missing') from None
    # Return a detached copy. Hash is an integrity check, not proof of origin.
    result = json.loads(json.dumps(value, ensure_ascii=False, allow_nan=False))
    return {'banner': f'Recorded live run · {date} · Nemotron 3 Nano via Nebius · protocol 4 · no new model calls',
            'recording': result}


def render_html(audit: dict) -> str:
    """Render a readable, inert facilitator timeline and the complete JSON."""
    def esc(value) -> str:
        if value is None:
            value = 'unavailable'
        elif isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False, sort_keys=True)
        return html.escape(str(value), quote=True)

    def fields(values) -> str:
        return ''.join(f'<dt>{esc(label)}</dt><dd>{esc(value)}</dd>' for label, value in values)

    def role_facts(value):
        if not isinstance(value, dict):
            return value
        return '; '.join(f'{role}: {", ".join(map(str, ids))}'
                         for role, ids in value.items() if isinstance(ids, list)) or 'none'

    def plan_summary(value):
        if not isinstance(value, list):
            return value
        return '; '.join(f"{item.get('action_id', 'unknown')}: owner {item.get('owner', 'unknown')}, "
                         f"status {item.get('status', 'unknown')}, handoffs {item.get('handoffs', [])}"
                         for item in value if isinstance(item, dict)) or 'No proposed actions'

    parts = []
    events = audit.get('events', [])
    if not isinstance(events, list):
        events = []
    for event in events:
        if not isinstance(event, dict):
            continue
        kind = event.get('type')
        heading = {'stage_release': 'Stage released', 'model_request': 'Model request',
                   'validation': 'Validation', 'coordinator_plan': 'Coordinator plan',
                   'decision': 'Human decision'}.get(kind, 'Recorded event')
        info = [('Stage', event.get('stage')), ('Time', event.get('at'))]
        if kind == 'stage_release':
            info.append(('Fact IDs by role', role_facts(event.get('fact_ids_by_role'))))
        elif kind == 'model_request':
            info.extend([('Role', event.get('role')), ('Provider', event.get('provider')),
                         ('Model', event.get('model')), ('Review mode', event.get('review_mode')),
                         ('Protocol', event.get('protocol_version')), ('Corpus', event.get('corpus_version')),
                         ('Request status', event.get('status')), ('Role status', event.get('role_status')),
                         ('Prompt attempted', event.get('prompt_attempted')),
                         ('Prompt SHA-256', event.get('prompt_sha256')), ('Token usage', event.get('usage')),
                         ('Latency (ms)', event.get('latency_ms')), ('Evidence IDs and SHA-256', event.get('evidence_refs'))])
        elif kind == 'validation':
            info.extend([('Role', event.get('role')), ('Status', event.get('status')),
                         ('Issue', event.get('issue')), ('Rationale issues', event.get('rationale_issues'))])
        elif kind == 'coordinator_plan':
            info.extend([('Plan', plan_summary(event.get('plan'))), ('Unresolved', event.get('unresolved')),
                         ('Round ID', event.get('round_id'))])
        elif kind == 'decision':
            info.extend([('Role', event.get('role')), ('Review mode', event.get('review_mode')),
                         ('Decision', event.get('decision')), ('Evidence fact IDs', event.get('source_ids'))])
        parts.append(f'<li><h2>{esc(heading)}</h2><dl>{fields(info)}</dl></li>')
    raw = html.escape(json.dumps(audit, ensure_ascii=False, indent=2), quote=True)
    metadata = fields([('Scenario', audit.get('scenario_id')), ('Exercise', audit.get('exercise_id')),
                       ('Current stage', audit.get('current_stage')), ('Audit SHA-256', audit.get('sha256'))])
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8"><title>YapLab exercise audit</title>'
            '<style>body{font:16px/1.5 system-ui;max-width:70rem;margin:2rem auto;padding:0 1rem;color:#17202a}'
            'li{padding:.5rem 0;border-bottom:1px solid #ddd}h2{font-size:1.1rem;margin:.5rem 0}'
            'dl{display:grid;grid-template-columns:minmax(9rem,13rem) 1fr;gap:.25rem 1rem}'
            'dt{font-weight:600}dd{margin:0;overflow-wrap:anywhere}'
            'pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f4f4f4;padding:1rem}'
            '@media(max-width:40rem){dl{display:block}dd{margin-bottom:.5rem}}</style></head><body>'
            '<h1>YapLab exercise audit</h1><p>Synthetic exercise; saved model output is unverified. '
            'The SHA-256 digest checks file integrity, not origin or legal authority.</p>'
            f'<dl>{metadata}</dl><h2>Timeline</h2><ol>{"".join(parts)}</ol>'
            f'<details><summary>Complete audit JSON</summary><pre>{raw}</pre></details></body></html>')
