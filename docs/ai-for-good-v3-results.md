# Protocol-3 live evaluation — 5 November 2026

The newly approved run completed **27 Nebius responses: 25 fully accepted, two
partial, zero unavailable roles**. Seven of nine snapshots had every role fully
accepted. All provider events reported success; that means a response returned,
not that its content was valid or relevant. The two partial roles are included
in the saved `structurally_failed_roles=2` count, not two additional failures.

The earlier attempt was denied before process creation. After the user explicitly
approved the corrected roughly $0.028 estimate, the operation was retried once
and permitted. The previous denial caused no requests; this run used the full
new 27-request allowance. There were no additional runs, retries, fallback or
provider switches.

## Scope, cost and provenance

- Provider/model: Nebius Token Factory,
  `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`, existing key/account.
- Inputs: synthetic staged role facts, curated action/question IDs, role
  instructions and public policy summaries. No real student data, media or
  project files were uploaded.
- Limits: 27 attempts, 400 output tokens each, no SDK retry/fallback; every
  response reported `stop`, with at most 185 output tokens observed.
- Reported usage: **46,864 input + 3,075 output tokens**. At the public Nano
  rates of $0.06/M input and $0.24/M output, the calculation is **$0.00354984**.
  This is a usage-based list-price estimate, not an invoice or verified account
  charge. The planning estimate was $0.02761824, without an enforced dollar cap.
  The [provider model page](https://nebius.com/services/token-factory/models/nvidia-nemotron-models-inference)
  was checked on 5 November; account-specific pricing/retention remain unverified.
- Source commit: `be5dd5d`; protocol `3`, corpus `2026-11-04.4`, general collection.
  All 27 prompt digests matched the reviewed plan. The run exercised the same
  coordination function as the app through the evaluation harness, not a live
  human-operated browser/provider session.

[Saved result](evidence/ai-for-good-coordination-live-v3-2026-11-05.json),
[actual synthetic responses](evidence/ai-for-good-coordination-responses-v3-2026-11-05.json)
and [offline review packet](evidence/ai-for-good-recorded-live-review-v3.html)
retain actual evidence. The packet shows saved source notes/IDs, not invented
plan prose. It can be opened without provider access. Earlier protocol-1/2
artifacts and the original protocol-2 packet remain unchanged.

## Two actual partial cases

| Case | Returned response | Retained by the app |
|---|---|---|
| Transcript disclosure, stage 1, privacy | `review_transcript_access` appeared twice: first td-1a/PDPL, then td-1b/England guidance | First proposal/evidence only, plus both valid questions; labelled partial / `duplicate_action_ids` |
| Caption failure, stage 2, teacher | Invented `resume_workshop_now`, followed by valid `delay_workshop` | Invalid action discarded; `delay_workshop` with its own cited evidence and both valid questions retained; labelled partial / `unknown_action_id` |

The model violated explicit uniqueness/allowed-ID instructions. No validator bug
was established, and the invented action was not mapped to another action by
assuming intent. Offline replay of every actual response checks the exact retained
items and issue labels. The existing partial-result handling worked during this
live run; it does not make invalid output fully accepted.

## Qualitative source-fit review

Independent agent review checked all 37 retained proposals against released role facts
and source candidates. None used a future-stage/other-role fact ID or an
out-of-candidate source ID. That is a boundary/ID finding, not evidence of good
citation choice. The following reviewed examples show mixed relevance:

| Saved example | Evidence-backed observation | Remaining limitation |
|---|---|---|
| Feedback, stage 3, teacher: `plan_human_feedback_review` with fg-2a/fg-2b, England + UNESCO | The cited guidance supports professional scrutiny and human-centred educational validation in its own context | It does not prescribe this fictional review or UAE university assessment procedures |
| Same action, stage 2, teacher: TDRA + PDPL | Valid candidate IDs, but these notes do not establish support for human review of AI feedback | Contextual/weak action-to-source fit; obtain assessment-specific institutional procedures |
| Transcript, stage 2, privacy: `review_transcript_access`, PDPL + England | Relevant to investigating access/data handling | Current UAE statutory text, applicable regime and local incident/retention rules are unresolved; England is comparative guidance |
| Captions, stage 2, teacher: retained `delay_workshop`, cf-2a, PDPL + TDRA | A conditional teaching decision can be reviewed alongside privacy/accessibility context | These sources do not decide postponement or prove an alternative usable |
| Captions, stage 3, teacher: `resume_vendor_workshop`, cf-3a + PDPL | Weak fact/source fit for vendor resumption | The plan correctly remains `missing_prerequisites` because `confirm_accessible_option` is absent; PDPL does not establish permission |
| Transcript, stage 1, accessibility: `offer_private_support`, td-1a | General inclusion/digital context exists | td-1c is the more direct released fact; the cited notes do not establish the exact private-contact procedure |

The source register's verified locators support these boundaries: [England DfE
responsible-use guidance](https://www.gov.uk/government/publications/generative-artificial-intelligence-in-education/generative-artificial-intelligence-ai-in-education)
principally concerns schools/colleges; [UNESCO GenAI guidance](https://unesdoc.unesco.org/ark:/48223/pf0000386693)
provides global human-centred guidance; [TDRA policy](https://dgov.tdra.gov.ae/-/media/dgov/pdfs/publications/national-digital-accessibility-policy-en.pdf)
Article 3 / Annex 1 has defined entity/public-service scope, not blanket private
university duties. Current UAE statutory full text/amendments were not verified.
These selected qualitative observations are not a complete expert semantic
assessment, a compliance determination or an educational outcome study.

## Lean application improvement and next steps

Each proposal's curated text now appears beside its own fact/source IDs inside
the existing collapsed **Sources and details** section, with a short relevance
prompt. This removes dependence on matching two separate lists by order. No new
user step, validator layer, automatic correction or provider retry was added.
The existing rendering test now covers two distinct evidence associations.

The remaining substantive work is institutional/source-fit review, broader
retrieval/evaluation coverage, a live browser/provider demonstration if wanted,
organiser KB/import instructions and final report/team/delivery details. No
hosted ingestion, publication, deployment or submission occurred. No further
paid run is implied by this completed allowance.

Verification passed **90 core checks, 102 policy/evidence tests and 98 frontend
tests**, plus frontend production build, both recorded-packet checks and both
scoped KB input checks. See the [verification record](evidence/ai-for-good-v3-verification-2026-11-05.json).
The recorded packet was inspected in a browser; the temporary loopback server
was stopped. Existing bundle-size and test WebSocket-port warnings remain; no
unrelated process was stopped.
