# Protocol-4 final-push status — 5 November 2026

**Implementation complete; paid app evaluation and actual replay are blocked on
approval.** No protocol-4 live outcome, rubric result, tokens or invoice charge
has been invented.

The final-push brief authorised up to 60 Nebius requests. The prepared operation
uses one 27-request pass through the actual local app: three scenarios × three
stages × three separate role requests. It uses the existing
`nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` key/account, synthetic facts and public
policy summaries, 400 output tokens per request and no retry/fallback/provider
switch. The app/driver use the same HTTP endpoints as Policy Lab; the driver
does not call the coordination harness directly. Facilitator decision text is
pre-authored and explicitly synthetic, not an educational user study.

Automatic approval review **denied process creation before execution**, stating
that the available user text did not explicitly authorise this exact new paid
run. Therefore the wrapper/server/driver did not start, no output directory was
created by that attempt, **provider attempts are zero and new inference cost is
$0**. A fresh explicit 27-request approval request is pending. No retry or indirect
provider execution followed the denial.

## What is ready

- Frozen corpus `2026-11-05.5`: 25 records, 13 source-text assets; 22/126 general
  and 25/135 UAEU documents/chunks. Three assets contain relevant sections, ten
  are attributed locator excerpts. Both local vector indexes are rebuilt.
- Actual app hybrid search with scope filters, lexical fallback and mode labels.
- Three candidate-gap debriefs and a team-authored 27-entry outcome rubric,
  committed before any final paid result.
- Protocol 4 public stated rationales, rationale-only rejection, per-request
  observed telemetry, ordered audit JSON/HTML and read-only recorded replay.
- The HTTP driver verifies provider/model/protocol/corpus before coordination,
  reserves three possible calls before each request and stops without retry on
  an uncertain HTTP result. It saves exact round responses and stage/final exports.
- The default offline demo remains scripted. Its rationales are correctly labelled
  scripted examples; actual model-assisted output is labelled model-written,
  unverified.

## Retrieval benchmark

Labels were authored and committed before retrieval rankings were inspected;
only unavailable-source corrections preceded evaluation. There are 36 positive
queries and four abstention cases, team-authored and not expert-validated.

| Retrieval | Recall@3 | MRR | MRR@3 | Correct abstentions |
|---|---:|---:|---:|---:|
| Lexical | 0.9722 | 0.9514 | 0.9444 | 3/4 |
| Hybrid | 1.0000 | 0.9444 | 0.9444 | 3/4 |

Hybrid did not improve MRR or solve every unrelated query. The
[benchmark artifact](evidence/ai-for-good-retrieval-benchmark.json) preserves all
queries, hashes and negative cases. These are not measured learning gains.

## Run and score after approval

The operator must start the local app with the approved Nebius settings and an
explicit synthetic-evaluation allowance. Normal process quotas are unchanged.
The driver defaults to a network-free plan:

```bash
cd apps/api
.venv/bin/python -B scripts/evaluate_policy_app.py
```

Once separately approved and the configured loopback server is running:

```bash
.venv/bin/python -B scripts/evaluate_policy_app.py --execute-live \
  --approval-reference USER_APPROVAL --api-url http://127.0.0.1:8897 \
  --output /tmp/NEW_EVIDENCE_DIRECTORY
```

This command can incur provider charges. Its maximum is 27 possible attempts,
within the brief's 60-request allowance; a reference string alone is not approval.
It does not read credentials. The prepared wrapper remains local in `/tmp` and
loads the existing key only into the backend process environment, never logs/files.

Then score exact final exports using the frozen rubric:

```bash
.venv/bin/python -B scripts/score_policy_outcomes.py \
  /tmp/NEW_EVIDENCE_DIRECTORY/transcript-disclosure.json \
  /tmp/NEW_EVIDENCE_DIRECTORY/caption-failure.json \
  /tmp/NEW_EVIDENCE_DIRECTORY/feedback-as-grade.json \
  --output /tmp/expected-actual.md --json-output /tmp/expected-actual.json
```

Actual accepted/partial/unavailable counts, rationale rejections, matches/misses,
tokens and cost remain **not run**. The list-price estimate will use reported
usage, with invoice verification explicitly false. The planning envelope is
under $0.10, not an enforced dollar cap. Older protocol-3 live results remain
historical and are not substituted for this run.

## Remaining limits

Actual replay browser verification needs an actual saved protocol-4 recording.
Current statutory UAE text, copyright, detailed CAA standards, current strategy
successors, expert/institutional validation, final team details and verified
five-page report pagination remain unresolved. Hosted ITU import, fine-tuning,
video production, publication and submission are outside this build's scope.

Final local verification: **90 existing backend checks, 124 policy/evidence/driver
tests, 3 real-vector tests and 100 frontend tests passed**. Both builds, scoped KB
checks, historical packet checks and extracted-wheel source-text/export smoke
passed. Browser verification used fake/scripted providers plus cached local
vectors; it was not a paid-model evaluation. See the [final evidence record](evidence/ai-for-good-final-push-2026-11-05.json).
