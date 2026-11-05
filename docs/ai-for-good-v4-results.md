# Protocol-4 app evaluation — 5 November 2026

**One approved live pass completed through the actual local app.** It returned
27 successful Nebius responses: **26 fully accepted roles, one partial and zero
unavailable**, across nine stages. Eight stages had all three roles fully
accepted. These are structural results, not semantic or educational success.

## Provenance and bounds

- Producer: clean commit `f2e22768ba56174ec3ae89b096238c84e2e5d90a`, protocol 4,
  frozen corpus `2026-11-05.5`; the frozen rubric was committed before this pass.
- Approval: `user-approved-2026-11-05-protocol4-27`. Prompt 11b and the user's
  explicit $5 budget authorised this pass. Its stricter bound was retained:
  **27 requests maximum, 400 output tokens each, no retries, fallback or provider
  switch**. No second pass was run. The earlier denied operation never started;
  this new approval resolved that historical blocker.
- Provider/model: existing Nebius account/key,
  `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`. Synthetic facts and public policy notes
  only; no real student records, slides, audio or project upload.
- The HTTP driver used the same exercise, advance, coordinate, decision and
  timeline endpoints as Policy Lab. Facilitator decisions were pre-authored,
  explicitly synthetic driver inputs, not observed educator decisions.
- [Exact evidence directory](evidence/ai-for-good-protocol4-live-2026-11-05/):
  nine exact app round responses, nine stage JSON/HTML pairs, three final pairs,
  [usage/provenance manifest](evidence/ai-for-good-protocol4-live-2026-11-05/manifest.json),
  and the later rubric comparison and browser screenshots. The manifest's 33
  listed file hashes verify. The separate verification record covers later files.
- All 27 actual prompt digests match the regenerated
  [protocol-4 plan](evidence/ai-for-good-coordination-plan-v4-2026-11-05.json).
  The plan's $0.03039144 input-envelope estimate was a proxy, not a token count or
  enforced dollar cap. The server was configured for the existing local MiniLM /
  scoped FAISS hybrid path; no embedding-provider requests were made. Per-role
  retrieval mode is not separately recorded, so digest agreement establishes
  the same offered notes, not an independent mode attestation for each request.

## Prompt alignment before execution

The rationale instruction now requests a plain operational explanation of why
released facts and cited notes support the action. It explicitly lists the
validator's screened legal words and forbids free text **outside rationale**.
The `_rationale()` validator is unchanged. Offline cases retain a plausible
operational rationale, reject a rationale containing “law” with
`rationale_legal_conclusion`, and preserve its otherwise valid proposal.
This remained protocol 4 because no live protocol-4 pass preceded the change.

## Actual outcomes and frozen-rubric score

| Scenario | Fully accepted roles | Partial | Unavailable | Rubric match | Partial match | Miss |
|---|---:|---:|---:|---:|---:|---:|
| Transcript disclosure | 9 | 0 | 0 | 0 | 7 | 2 |
| Caption failure | 9 | 0 | 0 | 4 | 4 | 1 |
| Feedback as grade | 8 | 1 | 0 | 4 | 4 | 1 |
| **Total** | **26** | **1** | **0** | **8** | **15** | **4** |

The feedback stage-3 teacher result was `partial`, with reason `invalid_response`
and issue `schema_limits`: no proposal survived, but its valid teaching-owner
question did. This is not a provider outage. The app round export does not retain
raw rejected provider text, so the exact malformed field cannot be reconstructed
from the fixed issue label. No whole role was unavailable. No retry repaired it.

The team-authored, not expert-validated rubric compares action, fact, source,
owner and applicable dependency IDs. Fully accepted means structural validation;
it does not mean rubric match. Transcript's missing action or mismatched fact/source
choices explain its seven partial matches and two misses. Three feedback rows
also lacked any expected source in the offered context, so they cannot demonstrate
a source match. The rubric was not changed to improve these scores.

Full per-row reasons are preserved in the
[Markdown comparison](evidence/ai-for-good-protocol4-live-2026-11-05/expected-actual.md)
and [JSON comparison](evidence/ai-for-good-protocol4-live-2026-11-05/expected-actual.json).

### One match, one miss, and substantive limits

**Match:** Caption stage 2, accessibility proposed `confirm_accessible_option`,
with fact `cf-2c` and `uae-persons-with-disabilities-education`. Its plan owner was
accessibility, status `awaiting_human_confirmation`. This satisfies the frozen
ID checklist; current statutory text/applicability remain unverified.

**Miss:** At that same stage, privacy proposed `protect_attendee_identity` with
`cf-1c`, omitting the expected `verify_vendor_terms` with `cf-2b`. The teacher's
`resume_vendor_workshop` consequently remained `missing_prerequisites`, with
privacy/accessibility handoffs visible. At stage 3 both prerequisite actions were
proposed, so resumption became `awaiting_human_confirmation`; no action executed.

Structural acceptance also left unsupported prose visible:

- Caption stage 2 privacy used only `us-ferpa-education-records` for identity
  protection. The saved FERPA note describes specified US-funded institutions
  and education records; this synthetic case does not establish those conditions
  or UAE applicability. It is a scoped foreign comparison, not a UAE requirement.
- Feedback stage 3 accessibility's `check_feedback_access` cited `fg-3a`,
  `uae-persons-with-disabilities-education` and `wcag-22-captions`, yet its rationale
  asserted an “EQA team” and “Al-Qasimi policy”. Those assertions are absent from
  the cited fact and offered source notes. They remain visible, model-written and
  unverified, rather than being edited out of the saved evidence.
- Feedback stage 2 `test_assistive_technology` cited a screen-reader fact but
  used the captions-specific WCAG note as support for screen-reader testing.
  That note alone does not establish the claimed connection, even where the
  provisional ID rubric matched.

A later improvement should target evidence selection and unsupported institutional
claims, followed by a separately authorised, prospectively scored experiment.
No additional guardrail or paid pass was added to obscure this run's failures.

## Stated rationale results

There were **38 retained proposals, 34 retained rationales and four rationale-only
rejections**. The proposal survives each rationale rejection:

| Scenario / stage / role / action | Saved omission reason |
|---|---|
| Transcript / 2 / teacher / `pause_transcript_sharing` | `rationale_legal_conclusion` |
| Transcript / 3 / accessibility / `confirm_support_option` | `rationale_legal_conclusion` |
| Feedback / 1 / teacher / `clarify_practice_feedback` | `rationale_length` |
| Feedback / 1 / privacy / `check_feedback_data` | `rationale_markdown` |

The wording alignment did not eliminate all rejected rationales. This single run
and earlier runs differ in protocol/corpus; no causal improvement is claimed.
The screen is a heuristic, not a truth or legal applicability check. Public stated
rationales are model outputs, not private chain-of-thought.

## Usage and list-price estimate

Reported usage was **53,330 input tokens and 4,182 output tokens**, with no missing
usage across 27 attempts. At recorded list prices of **$0.06/M input and $0.24/M
output**, the estimate is exactly **$0.00420348**:

`53330 × 0.06 / 1000000 + 4182 × 0.24 / 1000000`.

The [Nebius model page](https://nebius.com/services/token-factory/models/nvidia-nemotron-models-inference)
was checked earlier on 5 November. A later refresh was inaccessible; rates are
recorded list prices, not a verified invoice or billing-account balance.
`invoice_verified=false` is explicit in the manifest. The $5 approval was not an
enforced billing cap, and it did not remove the one-pass request limit.

## Browser replay and recording commands

All three final JSON exports were opened in the actual read-only UI. Each showed
the dated Nebius/protocol-4/no-new-calls banner, all three saved rounds, actual
proposal/rationale fields, conditional plans, ordered audit and candidate gaps.
Sources/details exposed all four `rationale_rejected` labels and their fixed
issues. Feedback stage 3 showed the actual partial teacher result and timeline
`schema limits` issue. There were no advance, generate or decision controls.
The launcher reported **hybrid for both general and UAEU** through local search.

Screenshots: [transcript](evidence/ai-for-good-protocol4-live-2026-11-05/replay-transcript.jpg),
[caption](evidence/ai-for-good-protocol4-live-2026-11-05/replay-caption.jpg),
[caption prerequisite](evidence/ai-for-good-protocol4-live-2026-11-05/replay-caption-prerequisite.jpg),
[feedback](evidence/ai-for-good-protocol4-live-2026-11-05/replay-feedback.jpg),
[actual partial result](evidence/ai-for-good-protocol4-live-2026-11-05/replay-feedback-partial.jpg).
[DOM checks](evidence/ai-for-good-protocol4-live-2026-11-05/browser-checks.json)
record each screen's banner, three plans, timeline, gaps and rationale count.

From the isolated checkout:

```bash
python3 scripts/run-hackathon-demo.py
python3 scripts/run-hackathon-demo.py --replay-live docs/evidence/ai-for-good-protocol4-live-2026-11-05/caption-failure.json
```

Run one launcher at a time on its default ports; Ctrl+C stops it before switching.
Substitute `transcript-disclosure.json` or `feedback-as-grade.json` for the other
recordings. [Recording guide](ai-for-good-demo.md) and
[exact hybrid setup](ai-for-good-local-kb.md#record-with-hybrid-retrieval) explain
what is on screen. Replaying creates no new provider requests.

## Checks and remaining limits

Local checks passed: **90 existing backend checks, 124 policy/evidence/driver
tests, three real-vector tests, 101 frontend tests and two launcher tests**.
Frontend build passed with the existing large-chunk warning. The final verification
record also records API build and unchanged corpus/bundle checks.

The actual run and replay are complete. Real educator/student testing, expert
assessment, current UAE statutory/IP/CAA coverage, institutional applicability,
final team fields, official-template five-page rendering and the new video remain
outstanding. No educational benefit, legal certification, hosted ITU import,
publication, deployment or submission is claimed. Historical protocols 1–3 and
the initial denied-operation record remain unchanged.
