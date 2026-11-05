# YapLab final-push readiness — 5 November 2026

**The approved live app evaluation and all three browser replays are complete.
Submission is not ready.** One 27-request pass returned 26 fully accepted roles,
one partial and none unavailable; the frozen rubric scored 8 match/15 partial/4
miss. Unsupported model-written claims remain documented. Nothing was pushed,
published, deployed or submitted. Prompt 11b targets this increment by 7 November,
12:00 ET; video/report preparation remains separate.

The user's work plan is corpus/protocol freeze by **7 November, 18:00 ET**, code
complete **8 November, 12:00 ET**, separate video work Sunday and official-template
report work Monday, aiming for submission Monday **9 November evening ET**. These
are the user's milestones. The [official event](https://aiforgood.itu.int/event/ai-for-good-sandbox-hackathon-united-arab-emirates/?topic=485)
lists 10 November without a verified cutoff/timezone. Initial video is optional,
max seven minutes, and required after shortlisting.

| Deliverable | Status | Evidence / remaining action |
|---|---|---|
| Primary material and scoped KB | Complete locally / coverage partial | 25 records; 13 text assets (three relevant-section assets, ten excerpts); general 22/126 and UAEU 25/135 documents/chunks. [Coverage/rights](ai-for-good-local-kb.md) and [search limits](ai-for-good-source-search.md) identify unverified national law, CAA detail, strategy successors and IP text. |
| App hybrid retrieval | Complete locally | Real local MiniLM/FAISS 126/135×384D, lexical fallback, scope filters and visible mode. Frozen 40-query [benchmark](ai-for-good-retrieval.md): recall@3 .9722/1.0, MRR .9514/.9444; both 3/4 correct abstentions. Team-authored, not expert validated. |
| Candidate gaps | Complete locally / validation partial | Three higher-education operational hypotheses with taxonomy, UAE reviewed coverage, scoped global examples and evidence needed. Stage 3 debrief verified in browser; institutional/expert review outstanding. |
| Protocol 4 rationale and audit | Complete locally | Public stated rationale with rationale-only rejection; ordered release/request/validation/plan/decision timeline and JSON/HTML. UI distinguishes scripted from model-written/unverified. No private chain-of-thought. Hashes are integrity, not origin/authentication. |
| Expected outcomes/scorer | Complete locally / labels provisional | 27 pre-authored scenario×stage×role entries; actual score: transcript 0/7/2, caption 4/4/1, feedback 4/4/1 match/partial/miss. Saved per-row tables. Not expert, legal or educational validation; source-fit review found unsupported claims despite ID acceptance. |
| App-level live test | Complete / substantive results mixed | One explicitly approved 27-request actual-app pass, all provider responses successful: 26 completed/one partial/zero unavailable, four rationale omissions. Reported 53,330 input/4,182 output tokens; list-price estimate $0.00420348, invoice unverified. [Actual results](ai-for-good-v4-results.md). |
| Recorded-live replay | Complete locally | All three real protocol 4 final exports browser-verified with dated no-new-calls banner, actual proposals/rationales, omission/partial labels, plans, timeline and gaps. [Screenshots and commands](ai-for-good-v4-results.md#browser-replay-and-recording-commands). Launcher auto-enables cached vectors and reports actual hybrid/lexical mode. |
| Offline demo | Complete locally | Browser verified typed classroom, Q&A/report, hybrid search, staged caption facts, scripted rationale labels, final gaps and recorded decision/audit. Default no-provider mode retained. [Recording guide](ai-for-good-demo.md). |
| ITU mappings | Complete locally / analogy | Actual SRC/C/PP/M/P/D/SINK, MLFO and ML sandbox counterparts; eight challenge perspectives cross-checked to Report 2.0's actual 13 dimensions/six factors. No conformance or readiness score. |
| Technical report | Partial | [Ordered draft](ai-for-good-report-draft.md) is below 2,000 words; team/contact/repository fields and supported official-template rendering/≤5-page verification remain. Older Library copy is unchanged. |
| Video | Separate work | Existing classroom recordings lack this final build; guide lists exact screen changes. No video file was modified or produced here. |
| Final external delivery | Blocked on inputs/approval | Need team details, final form/destination, deadline timezone and organiser KB acceptance/import instructions. No publication permission or submission is inferred. |

Current verification and evidence hashes are in the [11b record](evidence/ai-for-good-protocol4-live-2026-11-05/verification.json).
The [earlier record](evidence/ai-for-good-final-push-2026-11-05.json) preserves the initial denied state rather than rewriting history.
Older protocols 1–3 provider results and their static packets remain historical;
the latest protocol 3 result was 25 fully accepted/two partial, not a protocol 4
result or a semantic quality score. Fine-tuning, sandbox credits, hosted import,
a fourth role and classroom-to-policy transcript linking were explicitly outside
this build's scope.
