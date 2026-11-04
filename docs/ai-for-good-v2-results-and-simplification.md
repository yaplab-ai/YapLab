# Protocol-2 live result and simpler facilitator flow

One separately approved protocol-2 run used the existing Nebius key and unchanged
`b4394bd` prompt/validation implementation on 4 November 2026. It made exactly
27 calls to `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`, with a 400-output-token limit,
no retries, no fallback and no provider switch. Content was the reviewed synthetic
scenarios, YapLab role instructions/catalogs and public-policy paraphrases. No
real student data, transcripts, audio, slides or repository files were uploaded.
The allowance is consumed; no additional paid run was made.

| Measure | Protocol 1 | Protocol 2 |
| --- | --- | --- |
| Provider responses / attempts | 27 / 27 | 27 / 27 |
| Structurally accepted role responses | 14 / 27 | 24 / 27 |
| Snapshots with all three roles accepted | 1 / 9 | 6 / 9 |
| Reported input / output tokens | 26,604 / 3,289 | 40,132 / 3,412 |
| Reported-usage list-price estimate | $0.0023856 | $0.0032268 |

Protocol 2's remaining failures were `duplicate_action_ids` (transcript stage 1,
privacy), `schema_limits` (caption stage 3, teacher), and `unknown_source_id`
(feedback stage 3, teacher). The generic schema-limit label does not identify
which field exceeded its constraint; the source label means outside that role's
provided source list, not necessarily an invented document. Raw completions were
not retained. All 27 provider finish reasons were `stop`; the largest reported
output was 188 tokens, below the requested cap. No usage record was missing.

The estimate uses the recorded $0.06/M input and $0.24/M output list rates:
`(40132 * 0.06 + 3412 * 0.24) / 1000000 = $0.0032268`. It is not a verified invoice
or account-price/balance check. The billing owner and retention settings remain
unverified, as accepted for this bounded run. See the [recorded pricing source](https://nebius.com/services/token-factory/models/nvidia-nemotron-models-inference).

The observed structural result improved, but the run still failed the all-roles
criterion. These are two small, non-randomised runs on hand-authored cases, not
a general accuracy benchmark or proof that the prompt change alone caused the
difference. Accepted IDs do not establish policy correctness, institutional
authority or educational benefit. Semantic/expert review remains outstanding.
An offline recheck matched all 27 prompt/evidence snapshots to the approved
protocol-2 plan and revalidated the 24 accepted selections. The full
[redacted evidence](evidence/ai-for-good-coordination-live-v2-2026-11-04.json) is
separate from the unchanged protocol-1 artifact.

## Simplification after the run

The facilitator now has one **View role proposals** action. The server atomically
returns the saved round for the same exercise, stage and collection, or reserves
a new round. Reopening a completed view makes no new model call and consumes no
model-call quota. Partial/unavailable results retain their status. A pending
round returns a normal conflict; an explicit later retry loads the saved result.
The UI no longer tracks audit-lookup, uncertain-outcome or saved-round-ID locks.
Role/stage/scope changes clear the view and the same action retrieves the right
result. Model and source details are collapsed; there is one brief provider
disclosure instead of a recovery workflow.

Citation/ID validation, role and stage boundaries, live/offline labels, basic
request/call bounds and concise evidence records remain. The fixed diagnostic
codes stay in developer records; they add no user step. Their three concrete
categories helped interpret this run, so deleting them would lose useful evidence.
No additional guardrail framework or confirmation flow was added.

Saved-result replay is not an exactly-once billing guarantee: cancellation after
a call starts but before commit, or a process restart, can leave no saved result.
A deliberate retry may then start another call, subject to existing bounds.
No automated retry was introduced. The application remains disabled for new
coordination model calls by default, and no production setting was changed.


## Local verification

The final pass completed 90 existing backend checks, 71 policy-related unit
tests, the standalone scenario verifier and 97 frontend tests. Frontend and
offline API package builds passed. An extracted-wheel check returned the same
partial round twice with only three offline calls total. The independent
reviewer reproduced saved partial reuse, visible unavailable status, retained
scope filtering and stale-stage rejection without another call. Historical
protocol-1 evidence and both dry-run plans remain unchanged.
