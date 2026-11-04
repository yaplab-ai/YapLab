# YapLab Policy Lab technical report

**AI for Good UAE · Education · 4 November 2026**

Review draft for the organiser's template. Confirm team details and final
pagination before submission. This draft describes a locally tested prototype;
it does not claim legal compliance, educational effectiveness or deployment.

## 1. Use case and requirements

YapLab is a practice classroom of AI listeners. This extension targets university
teachers and teaching assistants rehearsing in English. Alongside explaining a
lesson to simulated students, an educator can examine the policies relevant to
using AI-supported teaching tools and practise responding when information is
incomplete. UAE sources form a reference case, with global and England examples
for comparison. The intended outcome is a more inspectable human review process;
improved teaching or governance outcomes have not been measured.

The prototype must retrieve attributable sources, distinguish their jurisdictions
and scope, release incident facts progressively, show different role views, and
record concise human decisions with evidence references. It must preserve the
existing classroom and work offline for repeatable software verification.

## 2. Implemented architecture

The existing React/Vite frontend connects to a FastAPI backend. Classroom
rehearsal already uses a session orchestrator, parallel listener agents,
source-grounded questions, moderation, answer evaluation and reports. The new
Policy Lab has source search, structured review, staged exercises and an optional
three-role coordination path.

The knowledge base is a packaged eleven-record catalogue of primary-source
metadata and original paraphrases, including authority, URL, locator, dates,
jurisdiction, document type and applicability cautions. Weighted lexical search
uses a limited, disclosed alias list for terms such as captions and screen
readers. This is a seed collection, not full-document ingestion, a distributed
vector database or a complete account of applicable policy.

General university context exposes eight sources; an explicit UAEU selection
adds three institution-only examples on student GenAI, data governance and
accommodation services. A source's presence does not prove legal applicability.
The legislation pages could not be directly re-fetched in the latest review;
their indexed provisions were corroborated and this limit is recorded.

Separate local Markdown input collections, provenance manifests and compatible
chunks are prepared for the inspected ITU-linked notebook. Its commit is pinned
in the package. No embeddings were built and no ITU-hosted import occurred. The
public reference code demonstrates local workflows; the hosted import contract
and final submission destination remain unconfirmed.

Review defaults to deterministic topic matching and source-consideration
selection. An explicit opt-in mode reuses the configured LLM client to choose
among retrieved source IDs and curated requirement indexes. Schema and citation
validation prevent the display of a model-invented source. Invalid output,
abstention, timeout or provider error yields a visibly labelled deterministic
fallback. This constrains output provenance; it does not prove relevance or
legal applicability. The separate coordination path has one bounded live-model
evaluation, described below; the free-text review selector was not live-tested.

## 3. Policy mapping and candidate domain gaps

The source catalogue includes UAE personal-data and disability legislation, AI
ethics guidance, national AI strategy, a school inclusion example, UNESCO and
England guidance, and three explicitly scoped UAEU institutional examples. School and
foreign examples are labelled as comparative material rather than assumed UAE
university obligations. The [source register](ai-for-good-policy-sources.md)
contains links and locators; each result retains its applicability cautions.

The scenarios expose three **candidate operational gaps** for institutional
review, rather than established defects in national law:

| Scenario | Information released over three stages | Question requiring institutional evidence |
| --- | --- | --- |
| Transcript disclosure | A disclosure is reported; sharing/retention facts emerge; a coordinated response is requested | Who owns containment, retention and communication when a rehearsal transcript identifies a learner? |
| Caption failure | Captions fail; alternative formats and vendor terms emerge; a tested fallback plan is requested | How should teaching, accessibility and privacy owners agree a usable alternative without unnecessary disclosure? |
| Practice feedback mistaken for a grade | A score causes confusion; gradebook and usability facts emerge; communication and review are needed | How should formative AI feedback be distinguished from official assessment and challenged when unclear? |

UNESCO and England sources provide examples for human review, privacy and
pedagogical scrutiny. The UAEU examples supply concrete institutional permissions and governance
processes. They do not establish duties for another university or resolve the
fictional incidents without their deployment facts and responsible reviewers.

## 4. Standards, supervision and audit

Our [Y.3172 mapping](ai-for-good.md#y3172-mapping-an-architectural-analogy) assigns
source, collector, preprocessing, model, policy, distribution and sink roles to
application components. It is a conceptual adaptation from the standard's
telecommunications context, not a conformance assertion. Citation validation and
human supervision constrain how model outputs are used.

The [AI Readiness 2.0 mapping](ai-for-good.md#ai-readiness-20-mapping) identifies
project evidence for data, infrastructure, skills, innovation and policy. No
national readiness score is calculated. Deployment capacity, energy use,
institutional adoption and educational value remain unevaluated.

An exercise has one shared stage counter and teacher, privacy and accessibility
views. Future facts are withheld; each view receives only its released facts.
Users can record a decision citing fact IDs. Optional coordination makes three
separate model requests, each receiving only its role's facts, mandate, policy
notes and stage-available action IDs. A deterministic coordinator validates IDs
and assigns owners, handoffs and dependencies; conflicts or missing input require
human review. This supports functional teaching/privacy/accessibility roles, not
authenticated institutional representatives or autonomous negotiation.

Coordination uses direct OpenAI-compatible clients with a 400-token output cap,
no retries or fake fallback, bounded concurrency and deadlines. It is disabled
by default. A stage change during inference prevents commit. A saved round pins
the corpus/protocol versions, provider/model, supplied source notes and hashes,
prompt hashes, call-attempt status and validated proposals. Facilitators can see
all role assessments; role audits return only their own. Auditability records
concise decisions and evidence without private model chain-of-thought. These
software paths have offline checks and one bounded live coordination run. Only
14 of 27 role responses passed structural validation; semantic quality is unreviewed.

## 5. Evaluation, limitations and reproduction

On the isolated `codex/yaplab-ai-for-good` worktree, 90 existing backend checks,
14 policy tests, six export tests, eleven coordination tests, eight coordination
HTTP tests, seven evaluation-harness tests, staged-scenario checks and 97
frontend tests passed. The frontend
production build and offline API wheel/sdist build succeeded. An extracted-wheel
API smoke check serves the scoped source collections and three scenarios.

The [offline evidence file](evidence/ai-for-good-offline.json) records four
hand-authored retrieval probes, all meeting their stated top-three or abstention
conditions. Three scenarios were traversed through all three stages and role
views: 27 deterministic reviews returned only corpus citation IDs. These checks
validate specific software behavior and packaging, not general retrieval
accuracy, legal reasoning quality, educator benefit or real-model behavior.

Input lengths, request admission, model-call slots, exercise capacity, action
counts and retention are bounded. State and quotas are process-local; restarting
clears them. These controls are not production authentication, tamper-resistant
audit storage or account-level cost control. Synthetic cases should be used:
pattern-based checks cannot reliably detect identifying information.

Before submission, obtain expert review of institutional applicability and
scenarios, broaden and benchmark the corpus, confirm the final submission
destination and hosted KB import contract, and repair the live run's structural
reliability gap before any further approved provider comparison. Final pagination has not been verified on this host. No publication, shared
repository update, deployment or application submission occurred during this work.
Reproduction commands and the explicit model opt-in are in the
[engineering runbook](ai-for-good.md#verification-and-local-use).


The independent implementation review repaired stale-stage writes, missing fact
references and inaccurate retrieval audit terms. Decisions and advances are now
conditional on the displayed stage; human decisions require released evidence.
Audit metadata distinguishes input words, alias expansion and topic anchors and
tracks the sources actually selected. These repairs improve traceability; they
do not validate policy advice. Exercise access expires after one hour, with lazy
cleanup rather than a guarantee of physical erasure at the exact expiry time.
The scenarios use fixed sequences and do not branch on decisions. The three-role
protocol has offline checks for independent contexts, invalid citations, conflicts,
dependencies, quota sharing, cancellation and stale commits. One approved Nebius
run made 27 requests with no retries or fallback. All returned provider responses;
14 passed schema/allowed-ID checks and 13 were rejected, leaving only one of nine
snapshots fully validated. Reported usage was 26,604 input and 3,289 output tokens,
corresponding to $0.0023856 at published list rates; the invoice was not verified.
The current coarse rejection label does not identify the precise failure cause.
This establishes provider access and a structural reliability gap, not policy
correctness or effectiveness. The original Anthropic configuration remains unchanged.
See the [review record](ai-for-good-independent-review.md) and
[live results](ai-for-good-live-results.md).
