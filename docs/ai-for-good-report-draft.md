# YapLab Policy Lab technical report

**AI for Good UAE · Education · 5 November 2026 · review draft**

Team/contact/repository fields and final five-page pagination remain to be
completed in the official template. This report distinguishes implemented
software, synthetic tests, recorded provider results and unmeasured outcomes.

## 1. Introduction

YapLab is an English-language practice classroom for university teachers and
teaching assistants. Its simulated listeners ask questions while an educator
rehearses a lesson; the session produces delivery and response feedback. Policy
Lab adds a separate, source-cited exercise about failures involving those same
kinds of artifacts: practice transcripts, captions/speech and feedback scores.
The classroom transcript is not automatically analysed by Policy Lab.

The intended value is an inspectable rehearsal of decisions under incomplete
information. Improved learning, accessibility, institutional governance or legal
compliance has not been measured. UAE material is a reference case for
education-domain operational questions, compared with explicitly scoped global
examples; the project does not recommend national policy changes.

## 2. Use case

A teacher or TA explains a lesson to simulated AI students, then practices a
policy incident. Three functional perspectives—teaching, privacy and
accessibility—receive different released facts. New stages reveal more
information. Separate model requests select conditional actions and citations;
a deterministic coordinator assigns owners, dependencies and handoffs. A
facilitator records a decision with evidence references.

These roles are simulation views, not authenticated institutional representatives.
The same Nano model can serve all three independent requests. The coordinator
merges constrained selections rather than performing autonomous negotiation or
executing actions. Teachers retain responsibility for judging relevance and
seeking their institution's procedures and qualified review.

## 3. Requirements and implementation

The React/Vite frontend connects to FastAPI. Existing rehearsal, speech and
report behavior is preserved. The extension implements:

- Attributable sources with dates, type, jurisdiction, institutional scope,
  verification notes, locators and reuse information.
- Source text and summary layers: real relevant sections or short locator
  excerpts support retrieval; original paraphrases remain the display layer.
- Hybrid lexical/local-vector retrieval with institutional filters, an explicit
  mode label and lexical fallback when optional vector setup is unavailable.
- Three incidents with three progressive stages and role-specific facts;
  future facts are withheld from role prompts.
- Protocol 4 proposals with action/fact/source IDs and a public stated rationale
  of at most 200 characters. Screening removes an invalid rationale alone while
  preserving valid proposal items. It is heuristic, not truth/legal verification.
  The UI labels model-written rationales unverified and scripted examples offline.
- An ordered audit timeline containing releases, request metadata, prompt/source
  digests, reported tokens, latency, validation, plans and facilitator decisions.
  JSON and self-contained HTML exports preserve modes and hashes.
- Final-stage candidate-gap debriefs, a team-authored outcome rubric/scorer and
  read-only replay of actual protocol-4 live exports.

The default demo uses fake/scripted providers, with no speech or model-provider
requests. Configured coordination uses the direct Nebius adapter, a 400-output-
token cap and no SDK retry/fallback. Saved stage results—including partial
results—are reused without new model calls. No private chain-of-thought is
requested or exposed; stated rationales are visible model outputs.

## 4. Mapping to ITU-T Y.3172

This is an **architectural analogy, not conformance**. [Y.3172](https://www.itu.int/rec/T-REC-Y.3172-201906-I/en)
clauses 3.2 and 8.1 describe telecommunications architecture, including these
components; our mappings identify inspectable application counterparts.

| Component | YapLab counterpart |
|---|---|
| SRC, source | `corpus.json`, hashed source texts and synthetic `scenarios.json` |
| C, collector | `load_corpus` and the scoped KB exporter |
| PP, preprocessor | Text chunking, lexical processing and normalized embeddings |
| M, model | Local MiniLM retrieval and bounded Nano role requests |
| P, policy | Response/citation validation, role/stage boundaries and conditional plan |
| D, distributor | Policy HTTP responses, role audit and facilitator timeline |
| SINK | Educator-facing proposals and the human-decision endpoint |
| ML function orchestrator, MLFO | Bounded coordination/store reservations; existing session orchestrator |
| ML sandbox | Local synthetic exercises, offline verification and saved-run comparison |

The policy node constrains model outputs; it is not merely the legal-document
collection. The prototype does not implement network placement, model training,
a telecommunication underlay or an ITU-managed sandbox.

## 5. Mapping to AI Readiness Report 2.0

The [challenge](https://aiforgood.itu.int/event/ai-for-good-sandbox-hackathon-united-arab-emirates/?topic=485)
lists eight perspectives. The January 2026 [Report 2.0](https://www.itu.int/dms_pub/itu-t/opb/ai4g/T-AI4G-AI4GOOD-2025-6-PDF-E.pdf)
contains six foundational factors and thirteen dimensions; it does not define
these eight lenses as its full dimensional structure. Our crosswalk is
project-level evidence, not an ITU assessment or national readiness score.

| Challenge perspective | Report dimension(s) | Evidence / limit |
|---|---|---|
| Open data and open-source management | 1 | Rights/hash metadata, MIT code; source coverage partial |
| Generative AI content ecosystem | 2 | AI rehearsal and attributed public outputs; no marketplace claim |
| Contextualisation and regional focus | 4, 12 | UAE/general/UAEU boundaries and foreign comparisons; no endorsement |
| Domain integration and cross-domain analysis | 3, 5 | Teaching/privacy/accessibility handoffs; real integration untested |
| Human interaction and supervision | 6, 8, 9 | Decisions, stated rationales, timeline and rubric; expert review outstanding |
| AI policy and implementation opportunities | 10 | Candidate gaps and evidence needed; no national-law deficiency inferred |
| AI for social inclusion | 11 | Caption and feedback scenarios; no measured access benefit |
| Digital infrastructure and energy | 13 | Local vectors, fallback and usage records; energy/scale unmeasured |

Detailed file/endpoint mappings and report page locators are in the
[engineering runbook](ai-for-good.md#ai-readiness-20-mapping).

## 6. Requirements mapped to local policies

Frozen corpus `2026-11-05.5` contains 25 records: 22 general and three explicit
UAEU institutional examples. Thirteen assets contain source text: three relevant-
section assets and ten short attributed locator excerpts. The UAE ethics PDF's
CC BY 4.0 sections cover scope and selected principles. Selected FERPA provisions
and DOJ accessibility guidance supply foreign full-section comparisons. Broader
reuse rights were not assumed where unclear.

Both notebook-input bundles are rebuilt and checked: general 22 documents/126
chunks; UAEU 25/135. Separate MiniLM/FAISS indexes contain 126/135 normalized
384-dimensional vectors with JSON provenance. Actual app search can combine
lexical and vector rankings; optional repository/model/index setup is required.
There is no distributed service or ITU-hosted import, and acceptance of the final
KB delivery format remains unconfirmed.

| Requirement | Reviewed reference and applicability limit |
|---|---|
| Personal-data handling | UAE PDPL indexed notes and ethics privacy principles; current statutory text, transfers and actual applicability unverified |
| Human oversight | UAE AI charter and non-binding ethics guidance; ordinary rehearsal is a voluntary reference case, not automatic significant-decision coverage |
| Accessibility | TDRA Article 3 / Annex 1 has defined entity/service scope; its WCAG 2.1 AA provision is not a blanket private-university duty |
| Higher-education quality/assessment | CAA outcomes overview supplies university context; former 2019 detailed standards were inaccessible |
| Institutional practice | UAEU student GenAI, governance and accommodation examples apply only within their own stated scope; student academic-credit policy does not automatically govern staff rehearsal |
| IP, strategies and infrastructure | Copyright-law text inaccessible; dated digital/cyber strategy references are contextual and do not establish current university obligations |

Global examples include EU education-risk classification/AI literacy, US FERPA
and public-entity web accessibility, WCAG 2.2 captions, Australian TEQSA, UK QAA
and OECD principles. Their territories, sectors, binding status and verification
limits remain explicit. School guidance from England/ADEK is comparative, not a
UAE university obligation. [Source search limits](ai-for-good-source-search.md)
record blocked endpoints and the bounded MoHESR search, which does not establish
that AI teaching guidance is absent.

## 7. Evaluation scenarios and evidence

| YapLab artifact failure | Progressive facts | Expected conditional outcome |
|---|---|---|
| Practice transcript identifies a learner | Sharing concern; access/retention facts; coordinated response request | Investigate/contain with an identified institutional owner and scoped data review |
| Captions/speech fail before a workshop | Service outage; alternatives/vendor terms; repeatable fallback request | Confirm a usable alternative and processing terms before any vendor-resumption plan |
| Practice feedback resembles an official grade | Confusion; gradebook/usability facts; correction/review request | Clarify formative status, identify a human review owner and provide an accessible explanation |

The pre-authored rubric covers all 27 scenario/stage/role combinations, including
acceptable/wrong actions, relevant facts/sources and expected ownership/dependencies.
It is **team-authored, not expert-validated**. The scorer produces expected/actual
match, partial or miss explanations from saved exports; ID matches do not prove
semantic correctness or legal applicability.

A separate 40-query retrieval benchmark was labelled and committed before
rankings were inspected: 36 positive and four abstention queries. Lexical
recall@3/MRR were 0.9722/0.9514; hybrid 1.0000/0.9444. MRR@3 was 0.9444 for both.
Both correctly abstained on three of four unrelated queries. Thus hybrid improved
this small set's top-three coverage, not MRR or all abstentions. These results are
not a representative domain benchmark, an expert evaluation or a causal result.
[Per-query evidence](evidence/ai-for-good-retrieval-benchmark.json) preserves hashes
and negative cases.

One explicitly approved protocol-4 pass through the actual local app used Nebius
Nano, synthetic/public-policy inputs, at most 27 requests×400 output tokens,
without retries or fallback. Clean producer commit: `f2e2276`. All 27 provider
responses succeeded: 26 fully accepted roles, one partial, none unavailable;
8/9 stages had all roles fully accepted. Feedback stage 3 teacher retained a
question but no proposal, with `schema_limits`. Four of 38 proposal rationales
were omitted: two screened legal-term cases, one length and one Markdown case.
34 remained model-written and unverified.

| Scenario | Rubric match / partial / miss |
|---|---|
| Transcript disclosure | 0 / 7 / 2 |
| Caption failure | 4 / 4 / 1 |
| Feedback as grade | 4 / 4 / 1 |

Caption stage 2 accessibility matched `confirm_accessible_option` with `cf-2c`
and the disability-education source. Privacy omitted `verify_vendor_terms`, so
the teacher's vendor-resumption plan remained `missing_prerequisites`. ID-level
matches still require substantive review: one accepted feedback rationale invoked
an unsupported “EQA team” and “Al-Qasimi policy”; a FERPA citation did not establish
US coverage or UAE applicability.

Reported 53,330 input/4,182 output tokens yield exactly $0.00420348 at recorded
$0.06/M input and $0.24/M output prices; invoice unverified. The
[manifest, exact app responses/exports and frozen-rubric comparison](evidence/ai-for-good-protocol4-live-2026-11-05/)
preserve successes and failures. All 27 prompt digests match the pre-run plan.
All three read-only recordings were browser-verified with actual outcomes,
rationale omissions, plans, ordered timeline, candidate gaps and a no-new-calls
banner. The 5 November classroom/report demonstration remains fake/scripted.
These are software and synthetic model observations, not measured educational
outcomes.

The separate 6 November live UI demo recorded 18 successful provider responses
(16 completed/two partial) across two caption exercises; the
[archived exports](evidence/ai-for-good-live-demo-2026-11-06/README.md) retain both
takes. Its facilitator decision was scripted synthetic input; this unscored demo
is distinct from the 5 November evaluation and establishes no educational outcome.

## 8. Candidate gaps and remaining validation

| Candidate operational gap | Scoped global comparison | Evidence needed |
|---|---|---|
| Unclear ownership of transcript access/retention and response | FERPA's defined education-record regime, within covered US institutions | Actual institutional incident, retention, access and provider procedures |
| Coordination of a tested caption fallback without unnecessary disclosure | WCAG caption criteria and US public-entity web rules; different scope and dates | Attendee usability tests, named teaching/access/privacy owners and vendor terms |
| Standards/process for distinguishing and challenging formative AI feedback | TEQSA/QAA higher-education guidance and use-dependent EU classification | Institutional assessment/feedback rules, actual score use and challenge/correction process |

These are deployment-level hypotheses, not established national legislative gaps.
The gap register records what the reviewed material establishes, what remains
unverified, source locators and needed evidence. Independent development-agent
review is not human expert or institutional validation.

Exercises/quotas are process-local, role views are not authentication, and file
hashes check integrity rather than origin. No legal certification, WCAG
conformance, educational gain, energy reduction or institutional adoption is
claimed. Team details, official-template pagination and final delivery/hosted-KB
instructions remain outstanding. No repository push, deployment or submission
has occurred.
