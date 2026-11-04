# YapLab · AI for Good UAE engineering plan

Working reference: **2026-11-04**. Product: an English-language practice classroom
for university teachers and teaching assistants, with a policy exercise alongside
the existing AI audience. UAE material supplies a reference case; the research
question concerns education-domain gaps that can be compared with global examples.

## Checkout and ownership

Hackathon implementation is isolated on **`codex/yaplab-ai-for-good`** in
`/Users/zukhriddin/Documents/HackathonProjects/YapLab-ai-for-good`. The branch
starts from locally available `origin/main` at `f0208f7`, which contains the
existing classroom and demo-hardening work. Only the policy addition and its
integration edits were transferred; the newer base's environment-example
defaults were retained.

The original Codex **Hackathons** checkout remains at
`/Users/zukhriddin/Documents/HackathonProjects/FrontRow`, on
`codex/remove-public-demo-links` at `92ae986`. Its tracked files are restored.
The original `.env`, both `.DS_Store` files and the user-provided `AGENTS.md`
are preserved. No secret environment file was copied into this worktree.
The `FrontRow-backend` and `FrontRow-data` worktrees were not modified.

This is a standard Git worktree. The app's managed-worktree attachment tool is
unavailable on this host, so commands must use the explicit directory above.
Local ignored dependency directories link to the original installed environment
to avoid reinstalling dependencies; those links are not Git artifacts. Do not
sync or upgrade packages through the shared virtual-environment links. For an
independent Python environment, use a fresh path such as
`UV_PROJECT_ENVIRONMENT=.venv-independent uv sync` in `apps/api` and use that
environment's Python in the commands below. Provision frontend dependencies
independently by replacing the local dependency-link directory with `npm ci`.

Development preferences are recorded in [AGENTS.md](../AGENTS.md): GPT-6.1 Sol
at `xhigh` for the lead, GPT-6.1 Terra at `xhigh` for delegated work. These
choices do not change the application's runtime models.

## Evidence and delivery boundaries

The existing classroom has a live Teaching bridge, parallel listeners, grounded
questions, moderation, answer review, a session report and deterministic replay.
Pitch and Interview should not be described as equivalent live implementations.
Existing Nebius measurements describe the earlier classroom implementation; they
are not measurements of the new policy workflow.

The new Policy Lab begins with curated source summaries and scoped retrieval,
evidence-led review, progressively released synthetic incidents, separate role
views, and human decision records. The UI and API must identify deterministic
review and any model-assisted mode. A role view does not establish an independent
institutional AI agent or access-control boundary. No legal certification,
educational efficacy, deployed governance, or autonomous institutional decision
making is claimed.

Source records contain original paraphrases, links, locators and applicability
cautions. The source documents retain their owners' rights. The repository's MIT
code license does not override source terms or the TalkMoves model/data license
(CC BY-NC-SA 4.0). Keep real learner information out of the prototype.

## Work sequence and acceptance criteria

| Increment | Acceptance criterion | Evidence |
| --- | --- | --- |
| 1. Preserve the classroom | Existing offline checks and frontend tests/build pass | Baseline: 90 backend checks, 86 frontend tests; frontend production build succeeded |
| 2. Source-linked seed KB | Official sources, dated metadata, law/guidance distinctions, university/school scope and global examples | [Corpus](../apps/api/frontrow/policy/corpus.json), [source review notes](ai-for-good-policy-sources.md) |
| 3. Policy review | Bounded requests, retrieved citations, explicit abstention, decision summary and mode; provider failure visible | `verify_policy.py`; no paid-provider result implied |
| 4. Staged incidents | Future facts withheld; teacher/privacy/accessibility views differ; bounded exercise state and decision audit | `verify_policy_scenarios.py` |
| 5. User workflow | Policy Lab reachable from Home; source links, search/review, next-stage controls, loading/errors | Frontend tests, production build and local visual check |
| 6. Submission evidence | Reproducible exercise output, limitations, architecture mapping and honest measured results | Local verification record and report outline below |

## Official requirements mapping

The [official brief and FAQs](https://aiforgood.itu.int/event/ai-for-good-sandbox-hackathon-united-arab-emirates/?topic=485)
set **10 November 2026** as the solution deadline. Required materials are a report
of at most five pages, a GitHub repository and a policy knowledge base; the
initial video is optional, with a seven-minute limit. Shortlisted teams need a
video. The brief calls for staged error scenarios, auditability, global policy
comparisons, and mappings to Y.3172 and AI Readiness 2.0. This document is a local
engineering plan, not a submission.

| Area | Current implementation/evidence | Work before claiming full coverage |
| --- | --- | --- |
| Education application | Existing multi-listener teaching rehearsal | University teacher/TA walkthrough and expert feedback |
| Knowledge base | Small versioned source catalogue and retrieval over curated summaries | Broader institution-specific corpus, source updates, retrieval benchmark, rights review and ITU KB ingestion |
| Policy reasoning | Retrieved evidence and scoped review; explicit review mode | Expert-labelled cases; bounded live-provider evaluation if enabled |
| Staged errors | Synthetic role-specific releases and recorded human decisions | Facilitated multi-person exercise and verified domain-gap conclusions |
| Coordination | One exercise timeline and distinct role views | Independent institutional-agent assessments and an explicit inter-agent protocol if included in final claims |
| Audit | Structured evidence/decision records | Retention policy, authorised audit access and tamper-resistant export for deployment |
| Standards mapping | Conceptual mapping below | Reviewer assessment; no certification claimed |

## Y.3172 mapping: an architectural analogy

[ITU-T Y.3172 (06/2019), clause 8.1.1](https://www.itu.int/rec/T-REC-Y.3172-201906-I/en)
describes an ML pipeline for telecommunications networks. Applying its component
roles to this education prototype is an analogy, not a claim of network-standard
conformance. In particular, its policy node constrains model outputs; it is not
simply a legal-document database.

| Pipeline role | YapLab counterpart | Check or limitation |
| --- | --- | --- |
| Source | Presenter speech, slides; curated policy records | Source provenance and synthetic policy-exercise facts |
| Collector | Transcript/PDF ingest; packaged corpus loader | Input limits, schema validation |
| Preprocessor | Transcript windowing, quote normalisation, retrieval tokenisation | Deterministic checks and retrieval trace |
| Model | Existing listener/summary/answer models; optional policy evidence selector | Offline doubles establish software behavior, not real-model quality |
| Policy | Grounding gates, citation validation, review abstention, human supervision | A cited reference cannot establish compliance |
| Distributor | REST/WebSocket delivery and policy API | Role/stage projection in the scenario API |
| Sink | Presenter/teacher and recorded human decision | No automatic grading, enforcement or student action |
| Orchestration/sandbox | Session orchestrator and staged synthetic exercise | No claim of an ITU-managed distributed sandbox |

## AI Readiness 2.0 mapping

The [January 2026 Report 2.0](https://www.itu.int/dms_pub/itu-t/opb/ai4g/T-AI4G-AI4GOOD-2025-6-PDF-E.pdf)
provides a framework for contextual self-assessment. These are proposed
project-level evidence choices, not a national readiness score.

| Perspective | Project evidence to inspect | Remaining uncertainty |
| --- | --- | --- |
| Data | Provenance, scope, freshness and retrieval tests | Seed completeness and retrieval relevance |
| Digital infrastructure | Local API/browser separation and bounded stores | ITU hosting, connectivity, energy and production scale |
| Digital skills | Teacher/TA synthetic walkthrough | Usability and actual teacher learning |
| Innovation ecosystem | Open code, reusable source records and recorded domain gaps | Participation, source rights and integration with institutional workflows |
| AI policy | Applicability cautions, global examples and human review | Institution-specific duties and expert validation |

## Verification and local use

All commands below run from the isolated worktree. No provider keys are needed for offline verification. Use the existing environment
or provision a fresh environment as described above. From the repository root:

```bash
cd apps/api
FRONTROW_LLM=fake FRONTROW_POLICY_LLM=off FRONTROW_TTS=none FRONTROW_STT=none .venv/bin/python verify.py
.venv/bin/python verify_policy.py
.venv/bin/python verify_policy_scenarios.py
.venv/bin/python scripts/evaluate_policy.py
```

From `frontend`, run `npm run test:live` and `npm run build`. To try the prototype,
start the API with fake classroom and disabled speech providers, then start Vite
with `VITE_API_URL=http://127.0.0.1:8000`. Open **Policy Lab** from Home.

```bash
# Terminal 1, from apps/api
FRONTROW_LLM=fake FRONTROW_POLICY_LLM=off FRONTROW_TTS=none FRONTROW_STT=none \
  .venv/bin/python -m uvicorn frontrow.server:app --host 127.0.0.1 --port 8000
# Terminal 2, from frontend
VITE_API_URL=http://127.0.0.1:8000 npm run dev -- --host 127.0.0.1
```

Policy exercises are in memory and expire; restarting the API clears them.
Use synthetic lesson descriptions and incidents. Review the API contract and
tests before enabling any provider-backed policy mode. Model-assisted operation
can send submitted text to the configured provider and consume that account's
credits; no such call is part of offline verification.

## Observed verification

The isolated worktree passed **90 existing backend checks**, **12 policy tests**,
the staged-scenario verification script, **91 frontend tests**, and a frontend
production build. `uv build --offline` produced an sdist and wheel using cached
build tools. An API smoke test imported an extracted wheel and served the scoped source collections and three scenarios; both JSON resources are packaged.

The [recorded offline walkthrough](evidence/ai-for-good-offline.json) contains
four hand-authored retrieval probes and three complete exercises, each with
three stages and three role views. All four retrieval probes met their stated
top-three/abstention conditions; all 27 role/stage reviews were deterministic
and returned corpus-only citation IDs. These are software smoke checks, not
a representative accuracy benchmark, legal review or educator study.

The frontend build retains its existing large-chunk warning. The package sdist
warns that `apps/api` has no standalone README. Neither prevented a successful
build. No live policy-provider calls, ITU-hosted import or external deployment
were used for this evidence.

## Policy API and operating limits

- `GET /policy/sources?institution=general|uaeu` serves scoped source notes; `POST /policy/search`
  accepts `query` (1–500 characters), `limit` (1–10), and optional `institution`.
- `POST /policy/review` accepts `text` (1–8,000 characters), optional `context`
  (up to 1,000), optional supported `topics`, and an explicit `institution` context. Search uses weighted lexical
  matching and a small, auditable alias list. Reviews select topic-relevant
  source considerations; the audit records query expansions and selected
  source/requirement IDs. Lexical absence is not evidence of a legal gap.
- `FRONTROW_POLICY_LLM=off` is the default. `configured` allows the existing
  configured LLM client to select only retrieved source IDs and requirement
  indexes. Invalid citations, abstention, timeout and provider errors fall back
  visibly to deterministic review. It does not produce free-form legal advice.
- General policy requests are capped at 120/client/hour and 10,000/UTC day.
  Model-assisted requests also have two concurrent slots, 8/client/hour,
  20/client/rolling day and 100/UTC day total. Busy or exhausted requests return
  HTTP 429 and Retry-After. These are process-local bounds, not account-level
  spending controls; restart or multiple workers change their effective scope.
- `GET /policy/scenarios`, `POST /policy/exercises`, and exercise `GET`,
  `/advance`, `/decision` and `/audit` routes implement staged synthetic cases.
  `?role=teacher|privacy|accessibility` selects a view. Decision `source_ids`
  refer to released **fact IDs**, while fact `policy_source_ids` refer to the
  corpus. The distinction prevents a citation to evidence the role has not seen.
- Exercises expire after one hour; at most 200 are retained, with 100 actions
  per exercise and a 500-character decision limit. Starts are capped at
  30/client/hour; other exercise requests at 240/client/hour. Roles are
  selectable views, not authenticated access controls. No real student data
  should be entered; limited pattern checks cannot guarantee de-identification.

## Report assembly and next decisions

The [technical report draft](ai-for-good-report-draft.md) is a reviewable content draft; its final layout has not been checked against the five-page limit. Use the [organiser's report template](https://s41721.pcdn.co/wp-content/uploads/2022/06/AI-for-Good-Sandbox-Hackathon-submission-template.docx)
for the final five-page document. Suggested allocation:

1. Problem, university teacher/TA use case, existing application and new scope.
2. Architecture, actual model/provider configuration, conceptual Y.3172 mapping.
3. Corpus method, applicability limits and local/global policy comparisons.
4. Staged exercise, expected vs observed software results, expert-review gaps.
5. Readiness mapping, limitations, reproducibility, source/repository references.

Before finalising, obtain an educator or policy review of the synthetic cases and verify the
institutional applicability of the added UAEU examples; establish the final ITU
submission destination and hosted knowledge-base import contract; decide whether to include live policy-model
results; and confirm team details. Team invitations and organiser correspondence
are separate from code implementation. Any final report must replace proposed
results with recorded observations and retain unresolved limitations.

Publication, deployment, sharing and submission require explicit user approval
after the concrete artifacts are reviewed.


## Current readiness handoff

The corpus now has **11 records**: 8 general sources and 3 additional UAEU-only
institutional examples. It covers laws, guidance, national strategy and university
practice. General search/review excludes the institutional entries; selecting
UAEU adds those examples without establishing affiliation or applicability.
Source verification and reuse notes are returned with the references. Direct
full-text re-verification of the two legislation pages remains incomplete after
HTTP 403 responses; no legal conclusions depend on treating those pages as newly
verified in full.

The [submission and import findings](ai-for-good-submission-workflow.md) pin the
inspected ITU-linked code, distinguish the Colab and simulation workflows, and
list the exact missing organiser instructions. The [local KB package](../knowledge-base/README.md)
contains separate scoped collections, manifests and notebook-compatible chunks.
Both collections pass deterministic regeneration checks. No embeddings, hosted
KB import, sandbox access, private-model reasoning trace or live policy-model
evaluation is claimed.

The [report content draft](ai-for-good-report-draft.md) is updated for these
results. Final DOCX authoring and pagination must be performed in a supported
local thread with the Documents bundled runtime. This host's dependency loader
does not provide that runtime; no unrendered document is labelled ready to submit.
