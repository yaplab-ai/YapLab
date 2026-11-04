# Sample proposal review and remaining work

Review date: 4 November 2026. Baseline: the saved protocol-2 run at `b4394bd`,
not a new model evaluation. This follow-up used offline fixtures and public
primary-source reading only. The 24/27 structural acceptance result is unchanged;
ID membership is not evidence that a citation supports an action.

## What the actual samples establish

| Saved sample | Source fit | Interpretation |
| --- | --- | --- |
| Transcript stage 2 teacher: pause sharing, citing disability law and school inclusion | Weak for that particular action | Inclusion material does not establish a transcript-distribution or incident-response procedure. The federal law's current text was not accessible in this pass. |
| Transcript stages 1/3 teacher: coordinate response, citing national AI strategy | Strategic context only | National AI talent/infrastructure/governance objectives do not specify the institution's incident owner, reporting route or particular containment action. |
| Feedback stage 2 teacher: human feedback review, citing school inclusion alone | Misaligned as the sole reference | School inclusion is not an AI-feedback accuracy or grade-review procedure. A professional-review principle is a more relevant comparison, but the institution's assessment rules are still needed. |
| Caption stage 2 teacher: delay workshop, citing privacy law and England GenAI guidance | Indirect/contextual | Those references can inform vendor/data checks; they do not determine when postponement is appropriate or which alternative works for the attendee. |
| Privacy proposals: ask about processing terms/access/retention | Relevant questions, applicability unresolved | The cited privacy/guidance notes help frame questions. They do not identify the actual controller, processor, legal regime or reporting duty in the fictional institution. |

The conditional action text is written by the application; the model selects
action and evidence IDs. The review therefore assesses both the curated action
and the chosen citation. It does not claim that the model generated legal advice.
No retrospective semantic score was assigned to the 24 accepted responses.

## Primary text inspected and boundaries

- [England DfE GenAI guidance](https://www.gov.uk/government/publications/generative-artificial-intelligence-in-education/generative-artificial-intelligence-ai-in-education): read the professional-judgement passage under Opportunities and challenges and the Data privacy/Formal assessments sections. It supports human scrutiny of AI outputs and attention to personal-data handling. It is principally an England school/college comparison; it does not supply UAE university rules or the exact transcript pause/grade-clarification procedure.
- [MoE inclusion overview](https://moe.gov.ae/en/Pages/DeterminationInclusiveEducation.aspx): inspected the 2020 school-policy scope and inclusion practices. It is an inclusion example, not a university incident policy.
- [UAE AI strategy](https://ai.gov.ae/strategy/): inspected Executive Summary and strategic objectives, including skills, infrastructure and governance context. It is not an operational incident-response procedure.
- [UAEU student GenAI policy](https://www.uaeu.ac.ae/en/about/pdfs/policies-2025/generative-ai-policy.pdf): inspected page 1 scope/header and page 4 Articles 3–4, including review and data-handling considerations. Its student academic-credit scope is not a universal teacher/TA obligation.
- [UAEU data-governance policy](https://www.uaeu.ac.ae/en/about/pdfs/policies-2025/data-governance-policy.pdf): inspected page 2 institutional-data definition and page 5 Article 4(8–9), including lifecycle/incident-management considerations. Institutional and research-data boundaries still matter; it does not prescribe the proposal's exact action.
- [UNESCO GenAI overview](https://www.unesco.org/en/articles/guidance-generative-ai-education-and-research): inspected its human-centred, privacy and educational-validation framing. This pass did not inspect every section of the linked complete publication. It is international guidance, not UAE legislation.
- UAE [personal-data law](https://uaelegislation.gov.ae/en/legislations/1972) and [disability law](https://uaelegislation.gov.ae/en/legislations/1172): both current official pages returned HTTP 403. Earlier indexed provisions and corpus notes are starting references; fresh full-text/amendment verification is still open. No access restriction was bypassed.

Only the specified PDF pages/sections were freshly reviewed, not every page.
UAEU references remain an explicitly selected institutional collection and were
not retroactively treated as sources in the general-scope live run.

## Focused implementation changes

Protocol 3 retains up to two independently valid proposals/questions. Invalid
siblings, excess items and repeated actions are omitted; a repeated action keeps
the first valid evidence set without merging. A role with remaining items is
labelled **partial**, remains a structural failure, and still needs review.
Malformed JSON/envelopes remain unavailable. Unknown citations and future/other
role facts are never substituted or forwarded. No extra user step was added.

The three saved failure labels were duplicate actions, a schema limit and an
unknown source ID. Raw rejected outputs were not retained, so synthetic fixtures
exercise those failure types without claiming recovery of those exact outputs.

Candidate ranking now uses the role's visible facts and current action text,
with teacher query context for privacy, accessibility or feedback review. The
PDPL was already education-tagged: it was eligible but previously outranked,
not categorically filtered out. Offline probes now place it in transcript teacher
candidates and England human-review guidance in feedback candidates. National
strategy and school-only inclusion remain in the KB/library, but are not offered
as operational support for these university incidents. With only those context
records available, the coordinator abstains instead of forcing citations.
This improves candidate availability, not measured citation accuracy. The prompt
also asks for sources relevant to the action and permits an empty answer.

New evidence includes locator and verification notes; old evidence remains
readable with its original hashes. The UI keeps one action and collapsed source
details, explains partial results plainly, and makes no semantic-support claim.
The separate [protocol-3 plan](evidence/ai-for-good-coordination-plan-v3.json) is
a network-free preparation artifact, not live evidence.

## Remaining requirements, in useful order

| Priority | Next concrete evidence/action | Current state |
| --- | --- | --- |
| 1 | An educator and institutional policy reviewer assess action–citation relevance and scenario plausibility using the samples above | Focused source review found weak/indirect matches; broad semantic validation is not complete |
| 2 | Choose an actual institutional reference scope and obtain its incident, accessibility, assessment/appeal and AI-use procedures | UAEU is an example collection; applicable mandates and owners are not established |
| 3 | Verify current authoritative legislation, amendments, scope/exclusions and relevant implementing instruments | Official law-page fetches returned 403; no legal applicability determination |
| 4 | If wanted, separately authorise a bounded protocol-3 model check and compare retained/partial/unavailable items and citation fit | No protocol-3 provider call is authorised or performed; previous allowances are consumed |
| 5 | Confirm organiser's final submission destination, exact cutoff/timezone, KB delivery/import contract and acceptance of summary-only material | Public reference notebook/export compatibility is implemented; hosted import/access remains unverified |
| 6 | Render the concise report in the official template, inspect every page, complete team/repository details and prepare a demo | Markdown draft exists; final DOCX pagination still needs the supported document runtime |
| 7 | Obtain explicit approval for repository publication, deployment or submission, then use the confirmed workflow | Nothing pushed, deployed, shared or submitted |

The [official brief](https://aiforgood.itu.int/event/ai-for-good-sandbox-hackathon-united-arab-emirates/?topic=485),
rechecked on this date, sets 10 November 2026 and requires a report of at most
five pages, a GitHub repository and a policy KB. Initial video is optional (up
to seven minutes); shortlisted teams need one. These artifacts still need the
domain-gap/global-example and standards/readiness mappings already drafted.
Keep code/source attributions and the TalkMoves licence boundary when packaging.

The operational questions exposed by the scenarios are candidate institutional
gaps, not established defects in UAE law. Real teacher learning, accessibility
outcomes, legal compliance and production readiness remain unmeasured.


The subsequent [three-PDF scope check](ai-for-good-verified-pdf-scopes.md) adds
TDRA digital-accessibility and AI ethics principles as scoped references and
tightens UAEU's student boundary. This narrows source uncertainty for those
specified policy pages; the statutory/current-text and actual-institution tasks
in priorities 2–3 remain open. No previous live outcome is recast as compliant.
