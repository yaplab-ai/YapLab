#!/usr/bin/env python3
"""Render the saved protocol-2 evaluation as a static, offline review packet."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_INPUT = ROOT / 'docs/evidence/ai-for-good-coordination-live-v2-2026-11-04.json'
DEFAULT_OUTPUT = ROOT / 'docs/evidence/ai-for-good-recorded-live-review.html'


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def source_link(url) -> str:
    value = str(url)
    try:
        parsed = urlsplit(value)
        allowed = parsed.scheme in ('https', 'http') and bool(parsed.netloc) and not any(ord(c) < 32 for c in value)
    except ValueError:
        allowed = False
    return f'<a href="{esc(value)}">{esc(value)}</a>' if allowed else esc(value)


def render(document: dict, input_sha256: str) -> str:
    """Render only saved fields; no current application, model, or corpus is loaded."""
    snapshots = document['snapshots']
    usage = document['usage']
    roles = [role for snapshot in snapshots for role in snapshot['roles']]
    if document.get('protocol_version') != '2' or len(snapshots) != 9 or len(roles) != 27 or len(usage) != 27:
        raise ValueError('Expected the recorded protocol-2 evaluation with 9 snapshots, 27 roles and 27 usage events')
    validated = sum(role['status'] == 'completed' for role in roles)
    passed = sum(snapshot['structural_validation'] == 'pass' for snapshot in snapshots)
    invalid = [role for role in roles if role['status'] != 'completed']
    categories = Counter(role.get('validation_issue', 'unclassified') for role in invalid)
    scenario_names = {
        'transcript-disclosure': 'Transcript disclosure',
        'caption-failure': 'Caption failure',
        'feedback-as-grade': 'Feedback mistaken for a grade',
    }

    overview = []
    detail_sections = []
    for snapshot_index, snapshot in enumerate(snapshots, 1):
        scenario = snapshot['scenario_id']
        stage = snapshot['stage']
        name = scenario_names.get(scenario, scenario)
        status_cells = []
        details = []
        for role_index, role in enumerate(snapshot['roles'], 1):
            anchor = f'role-{snapshot_index}-{role_index}'
            failure = (' · ' + role['reason'] if role.get('reason') else '') + (
                ' · ' + role['validation_issue'] if role.get('validation_issue') else '')
            status_cells.append(f'<a href="#{anchor}">{esc(role["role"])}: {esc(role["status"])}{esc(failure)}</a>')
            proposals = []
            for proposal in role['proposals']:
                proposals.append('<li><strong>Action:</strong> <code>' + esc(proposal['action_id']) +
                                 '</code><br><strong>Fact IDs:</strong> ' + esc(', '.join(proposal['fact_ids'])) +
                                 '<br><strong>Source IDs:</strong> ' + esc(', '.join(proposal['source_ids'])) + '</li>')
            evidence = []
            for item in role['evidence']:
                optional = ''.join('<br><strong>' + label + ':</strong> ' + esc(item[key])
                                   for key, label in (('source_locator', 'Source locator'),
                                                      ('verification', 'Verification')) if key in item)
                limits = ''.join('<li>' + esc(limit) + '</li>' for limit in item['limitations'])
                evidence.append('<li><strong>' + esc(item['title']) + '</strong> <code>' + esc(item['id']) +
                    '</code><br>' + source_link(item['url']) + '<br><strong>Authority:</strong> ' + esc(item['authority']) +
                    ' · <strong>Type:</strong> ' + esc(item['document_type']) +
                    ' · <strong>Jurisdiction:</strong> ' + esc(item['jurisdiction']) +
                    ' · <strong>Institution:</strong> ' + esc(item['institution'] if item['institution'] is not None else '—') +
                    '<br><strong>Scope:</strong> ' + esc(item['scope']) +
                    '<br><strong>Summary:</strong> ' + esc(item['summary']) + optional +
                    '<br><strong>Limitations:</strong><ul>' + limits + '</ul>' +
                    '<strong>Saved note SHA-256:</strong> <code>' + esc(item['sha256']) + '</code></li>')
            details.append(f'<details id="{anchor}"><summary>{esc(role["role"])} · {esc(role["status"])}{esc(failure)}</summary>' +
                '<p><strong>Prompt attempted:</strong> ' + esc(role['prompt_attempted']) +
                '<br><strong>Prompt SHA-256:</strong> <code>' + esc(role['prompt_sha256']) + '</code></p>' +
                '<h4>Saved proposals</h4>' + ('<ul>' + ''.join(proposals) + '</ul>' if proposals else '<p>No saved proposals.</p>') +
                '<p><strong>Question IDs:</strong> ' + (esc(', '.join(role['question_ids'])) if role['question_ids'] else 'None saved.') + '</p>' +
                '<h4>Supplied source notes</h4><ul class="sources">' + ''.join(evidence) + '</ul></details>')
        overview.append('<tr><th scope="row">' + esc(name) + '<br><small>' + esc(scenario) + '</small></th><td>' +
            esc(stage) + '</td><td>' + esc(snapshot['structural_validation']) + '</td><td>' + '<br>'.join(status_cells) + '</td></tr>')
        plan = []
        for item in snapshot['plan']:
            plan.append('<li><strong>Action:</strong> <code>' + esc(item['action_id']) +
                '</code> · <strong>Owner:</strong> ' + esc(item['owner']) + ' · <strong>Status:</strong> ' + esc(item['status']) +
                ' · <strong>Dependencies:</strong> ' + (esc(', '.join(item['depends_on'])) if item['depends_on'] else 'None saved') + '</li>')
        detail_sections.append('<section class="snapshot"><h3>' + esc(name) + ' · stage ' + esc(stage) +
            '</h3><p>Saved structural result: <strong>' + esc(snapshot['structural_validation']) + '</strong>.</p>' +
            ''.join(details) + '<h4>Saved merged plan</h4>' +
            ('<ul>' + ''.join(plan) + '</ul>' if plan else '<p>No saved plan items.</p>') + '</section>')
    usage_rows = []
    for event in usage:
        usage_rows.append('<tr>' + ''.join('<td>' + esc(event.get(key) if event.get(key) is not None else '—') + '</td>'
            for key in ('scenario_id', 'stage', 'role', 'outcome', 'finish_reason', 'error_type', 'latency_ms', 'input_tokens', 'output_tokens')) + '</tr>')
    issue_text = ', '.join(f'{key}: {count}' for key, count in sorted(categories.items())) or 'None saved'
    return '''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>Recorded live-provider coordination review | YapLab</title>
<style>
:root{color-scheme:light;--ink:#172739;--muted:#4e6171;--line:#cbd6d7;--accent:#125c60;--paper:#f5f7f5}
*{box-sizing:border-box}body{margin:0;color:var(--ink);background:var(--paper);font:16px/1.55 system-ui,-apple-system,sans-serif}main{max-width:1160px;margin:auto;padding:2.5rem 1.25rem 5rem}h1,h2,h3,h4{line-height:1.2}h1{font-size:clamp(2rem,5vw,3.5rem);max-width:18ch;margin:.3rem 0 1rem}h2{margin-top:3rem}h3{font-size:1.25rem}.eyebrow{text-transform:uppercase;letter-spacing:.13em;color:var(--accent);font-size:.8rem;font-weight:700}.lead{font-size:1.15rem;max-width:75ch}.note{background:#e5efec;border-left:4px solid var(--accent);padding:1rem 1.2rem}.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:.75rem;margin:2rem 0}.stat,.snapshot{background:white;border:1px solid var(--line);border-radius:.65rem;padding:1rem}.stat strong{display:block;font-size:1.65rem;color:var(--accent)}.stat span,small{color:var(--muted)}.table-wrap{overflow-x:auto}table{border-collapse:collapse;width:100%;background:white;font-size:.9rem}th,td{border:1px solid var(--line);padding:.55rem;text-align:left;vertical-align:top}th{background:#e8efed}code{overflow-wrap:anywhere;font-size:.86em}a{color:#07575d;overflow-wrap:anywhere}details{border-top:1px solid var(--line);padding:.7rem 0}summary{cursor:pointer;font-weight:700}li{margin:.5rem 0}.sources>li{margin:1rem 0}.snapshot{margin:1rem 0}.muted{color:var(--muted)}
</style></head><body><main>
<p class="eyebrow">YapLab · historical evidence</p>
<h1>Recorded coordination, open for review</h1>
<p class="lead"><strong>Recorded live-provider evidence, viewed offline; no new provider calls.</strong> This packet displays saved synthetic-exercise results from protocol 2. The current application uses a later protocol; this record is not a current-protocol result.</p>
<div class="stats"><div class="stat"><strong>''' + esc(validated) + ''' / 27</strong><span>structurally accepted role responses</span></div><div class="stat"><strong>''' + esc(passed) + ''' / 9</strong><span>snapshots with every role structurally accepted</span></div><div class="stat"><strong>''' + esc(document['provider_success_events']) + ''' / 27</strong><span>provider events reported success</span></div></div>
<div class="note"><strong>What this shows.</strong> The model selected from constrained, prewritten actions and IDs. The application validated and merged those selections; this is not free-form generation or multi-institution negotiation. Structural acceptance is not a semantic, legal, accessibility, or learning score. Human semantic quality remains unreviewed. Raw rejected outputs are unavailable. Review the <a href="../ai-for-good-source-review-and-next-steps.md">source-fit review and known weak matches</a> before interpreting individual citations.</div>
<h2>Record provenance</h2><p><strong>Input JSON SHA-256:</strong> <code>''' + esc(input_sha256) + '''</code><br><strong>Protocol:</strong> ''' + esc(document['protocol_version']) + ''' · <strong>Corpus:</strong> ''' + esc(document['corpus_version']) + ''' · <strong>Source commit:</strong> <code>''' + esc(document['source_commit']) + '''</code><br><strong>Provider:</strong> ''' + esc(document['provider']) + ''' · <strong>Model:</strong> <code>''' + esc(document['model']['model']) + '''</code> · <strong>Evaluation date:</strong> ''' + esc(document['evaluation_date']) + '''</p>
<p class="muted">Recorded validation issue categories: ''' + esc(issue_text) + '''. These labels describe validator failures; they do not reconstruct rejected content. Source notes are the saved historical notes, including their then-recorded caveats; they are not an update to current law or institutional policy.</p>
<h2>Nine recorded snapshots</h2><div class="table-wrap"><table><thead><tr><th scope="col">Scenario</th><th scope="col">Stage</th><th scope="col">Structural result</th><th scope="col">Roles and recorded failures</th></tr></thead><tbody>''' + ''.join(overview) + '''</tbody></table></div>
<h2>Role selections and saved plans</h2><p>Expand each role for its saved IDs, the exact supplied source notes and the recorded failure label, if any. Merged plans below reproduce saved action IDs, owners, statuses and dependencies; the record did not save plan prose.</p>''' + ''.join(detail_sections) + '''
<h2>Provider usage events</h2><p>These are the 27 saved provider events. A successful provider event means a response was returned; it does not imply that downstream structural validation passed. Usage and estimated cost are not invoice verification.</p><div class="table-wrap"><table><thead><tr><th scope="col">Scenario</th><th scope="col">Stage</th><th scope="col">Role</th><th scope="col">Outcome</th><th scope="col">Finish</th><th scope="col">Error type</th><th scope="col">Latency ms</th><th scope="col">Input tokens</th><th scope="col">Output tokens</th></tr></thead><tbody>''' + ''.join(usage_rows) + '''</tbody></table></div>
</main></body></html>\n'''


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=DEFAULT_INPUT)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--check', action='store_true', help='compare existing HTML with current recorded input')
    args = parser.parse_args()
    try:
        if args.input.resolve() == args.output.resolve():
            raise ValueError('input and output must differ')
        raw = args.input.read_bytes()
        html_bytes = render(json.loads(raw), hashlib.sha256(raw).hexdigest()).encode('utf-8')
        if args.check:
            if args.output.read_bytes() != html_bytes:
                raise ValueError('review packet differs from saved input')
            print(f'Recorded review verified: {args.output}')
        else:
            if args.output.is_symlink():
                raise ValueError('output may not be a symlink')
            args.output.write_bytes(html_bytes)
            print(f'Recorded review prepared: {args.output}')
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(1, f'Recorded review failed: {exc}\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
