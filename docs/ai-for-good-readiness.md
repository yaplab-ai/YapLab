# YapLab submission readiness — 4 November 2026

**Not ready to submit.** The local demonstration and draft evidence are ready for
review. Final report production, delivery details and key evidence gaps remain.
This assessment starts from local commit `190aeec`; nothing has been uploaded,
pushed, deployed or submitted.

The [official brief and FAQ](https://aiforgood.itu.int/event/ai-for-good-sandbox-hackathon-united-arab-emirates/?topic=485),
rechecked today, list a five-page technical report, GitHub repository and knowledge
base. Initial video is optional (seven-minute maximum), becoming required for
shortlisted teams. The submission date is 10 November 2026; the reviewed page does
not give a cutoff time or timezone. The FAQ lists report topics and asks a video
to distinguish expected and actual outcomes.

Status meanings: **Complete locally** = present and checked for the stated scope;
**Partial** = useful evidence exists but does not fully support the requirement;
**Blocked** = a specific input/access/runtime or authorisation is needed;
**Missing** = no corresponding final artifact/evidence exists.

| Item | Status | Exact artifact/evidence and remaining action |
|---|---|---|
| Teaching → report → policy exercise demonstration | Complete locally | [Six-minute guide](ai-for-good-demo.md), launcher and [browser evidence](evidence/ai-for-good-demo-2026-11-04.json). Fake classroom, deterministic review, scripted proposals; policy exercise is selected separately, with no automatic transcript analysis. |
| Progressive errors and audit implementation | Complete locally | Three scenarios × three stages; released role-specific facts, human decisions, evidence references and optional coordination. [Implementation/tests](../apps/api/frontrow/policy/) and browser audit checks. Role selection is not access control. |
| Technical report | Partial / blocked | [Content draft](ai-for-good-report-draft.md) includes use case, requirements, mappings, scenarios, candidate gaps and results. Team/contact/repository fields are missing. [Template rendering](ai-for-good-rendering-handoff.md) needs a supported Documents runtime; no final DOCX/PDF or verified ≤5-page pagination exists. |
| GitHub delivery | Partial / blocked | Code is isolated on `codex/yaplab-ai-for-good`, with MIT code and separate TalkMoves terms retained. Confirm the repository destination/access and approve publication of the chosen content. No hackathon branch publication or final submission URL is established. |
| Knowledge-base content | Partial | Corpus `.4`: 10 general references plus three explicit UAEU examples. Both notebook-input bundles pass `--check`: 10/29 and 13/38 documents/chunks. They contain summaries/provenance, not full source texts. Current PDPL, cross-border conditions and institutional applicability remain unverified. |
| Vectorised / ITU-hosted KB | Blocked; artifacts missing | Both manifests state `embedding_index_built=false` and `hosted_import_verified=false`. [Reference workflow](ai-for-good-submission-workflow.md) is inspected, not executed as hosted ingestion. Organiser must confirm format, summary/full-text acceptance, endpoint/access and timing. No FAISS/Chroma index or ITU receipt exists. |
| Actual policy-agent provider evidence | Partial | Two historical runs exist; protocol 2 recorded 27 separate role requests, 24 accepted contracts, 6/9 fully accepted snapshots. [Recorded evidence viewer](evidence/ai-for-good-recorded-live-review.html) shows actual saved selections, failures and source notes. Current protocol 3/corpus `.4` has no live-provider run. |
| Domain gaps, global examples and source relevance | Partial | [Source-fit review](ai-for-good-source-review-and-next-steps.md) identifies weak/indirect historical matches. Transcript ownership, caption fallback and formative-feedback/grade boundaries are candidate operational gaps. An educator and institutional policy reviewer have not validated these findings or applicable mandates. |
| Standards / readiness mapping | Partial | [Y.3172 and Readiness 2.0 mapping](ai-for-good.md#y3172-mapping-an-architectural-analogy) is drafted as an architectural analogy. No conformance assessment, national readiness score, energy measurement or adoption result is claimed. |
| Audit format acceptance | Blocked on clarification | Concise decision summaries, stage/role, source references, hashes and modes exist. The brief requests reasoning traces; confirm that these reviewable summaries satisfy it. Private model chain-of-thought is neither requested nor exposed. |
| Sandbox credits / fine-tuning | Missing; applicability unconfirmed | No ITU sandbox use or fine-tuned model. The brief mentions these resources; clarify whether this inference prototype must demonstrate them and how selected-participant access works. |
| Video | Missing; optional initially | Walkthrough and screenshot exist; no video recorded. User must choose whether to record now. Shortlisting would make video delivery required. |
| Final delivery instructions and team details | Blocked | Initial registration acknowledgment is not final acceptance/submission. Need final form/destination, detailed team sheet, lead/member/contact details (maximum four people per public brief), exact deadline/timezone and KB instructions. |

## What the live evidence does and does not demonstrate

The brief allows **one or more** listed agent roles. It does not explicitly demand
all four role types or a new real-time provider request during initial submission.
However, a scripted UI walkthrough alone is weak evidence for its AI-agent
capability criterion. That is an assessment of the evidence gap, not an invented
organiser rule.

The saved protocol-2 run used independent role-specific model requests over
synthetic staged cases. Models selected curated action/fact/source IDs; application
code supplied the action wording and assembled a conditional plan. The result is
not autonomous negotiation between authenticated institutions. It was a harness
run over stage snapshots, not a recorded human-operated browser/provider session.
The current offline demo's teacher vendor-route proposal differs from the saved
caption-stage-2 teacher choice (`delay_workshop`); never substitute one for the other.

The [historical viewer](evidence/ai-for-good-recorded-live-review.html) makes those
actual saved choices inspectable without new calls. It preserves protocol 2,
corpus `.3`, source commit, prompt/source digests and all three failed-role statuses.
Raw rejected completions were not retained. Its accepted selections have not
received a complete expert relevance assessment; 24/27 is a contract-validation
count, not citation quality, legal compliance or learning gain.

For stronger current evidence, the next experiment would use the existing
[protocol-3/corpus-.4 dry-run plan](evidence/ai-for-good-coordination-plan-v3-corpus4.json)
under a separately authorised provider allowance, plus human source-fit review.
A human-operated model-assisted demonstration would additionally establish the
current browser-to-provider path. Neither has been run or scheduled. Earlier
allowances are consumed; this checklist authorises no further requests.

## Decisions and inputs needed, in priority order

1. **Organiser instructions:** supply the final submission/team sheet, exact
   cutoff/timezone and KB access/format rules if already received. Confirm
   summary-corpus acceptance, hosted-index timing, audit-summary acceptance and
   sandbox/fine-tuning expectations. Questions are drafted in the workflow doc;
   none were sent.
2. **Report identity and delivery:** confirm lead/member/contact details and the
   repository URL/access/publication scope, then render and inspect the official
   template in a supported runtime. Publication and submission still require
   explicit authorisation.
3. **Evaluation:** nominate an educator/policy reviewer and choose an actual
   institutional scope if available. Otherwise retain the explicitly synthetic,
   conditional reference case. Decide whether a new bounded current-protocol
   provider run or browser/provider recording is wanted; scope/cost approval is
   still needed before paid calls.
4. **Video:** choose an optional initial recording using the guide, clearly
   separating offline demo, historical provider evidence and expected outcomes.

The most useful work possible without those inputs was to make the historical
provider evidence directly inspectable and link this checklist to actual files.
No legal certification, real educational outcome or hosted acceptance is implied.

Local verification of this increment: three recorded-viewer tests, deterministic
HTML `--check`, both scoped KB bundle checks, changed-document link checks and a
browser inspection passed. See [the verification record](evidence/ai-for-good-readiness-2026-11-04.json).
To reproduce the viewer check from `apps/api`:

```bash
.venv/bin/python -B verify_recorded_live_review.py
.venv/bin/python -B scripts/export_recorded_live_review.py --check
```
