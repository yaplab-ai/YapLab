# YapLab: six-minute local demo

This walkthrough connects the existing classroom to a separate, human-selected
Policy Lab exercise. It does **not** automatically review a classroom transcript
against policy. Use synthetic text and the built-in deck throughout.

## Start and stop

From the repository root, with API `.venv` and frontend `node_modules` already
installed:

```bash
python3 scripts/run-hackathon-demo.py
```

Open `http://127.0.0.1:5179`. Both the app header and classroom say **Offline demo**.
The launcher binds only to loopback, starts the API on 8765, sets fake classroom
LLM, speech providers off, deterministic policy review and scripted coordination.
It installs nothing. Camera and audio start off. The frontend demo flag controls
labels only; use this launcher to pair it with the enforced fake/no-speech backend.
The page may request its existing Google Fonts; fallback fonts work without that
network resource. “Offline” here describes synthetic application behavior and
no model/speech-provider calls. Do not press Speak or upload a
file for this walkthrough. A provider call is not needed.

If a port is occupied, the launcher stops without touching that process. Pick
alternatives and open the printed address:

```bash
python3 scripts/run-hackathon-demo.py --api-port 8875 --ui-port 5189
```

Ctrl+C stops the two processes started by this command. Restarting clears the
server's temporary sessions, exercises and audit events. Browser refresh returns
the app to Home; it does not restore an exercise. This is a local rehearsal setup,
not a deployment. Default application coordination remains off outside this
launcher; `FRONTROW_POLICY_COORDINATION=demo` explicitly opts into scripted
proposals and rejects configured network/speech providers.

## Presenter walkthrough

1. **0:00–1:30 · Classroom and report.** Click **Start teaching**, keep the demo
   deck, then **Enter the classroom**. Type the paragraph below into **Type to the
   room**, click **Send**, and advance a slide. After a few seconds choose **End
   talk**, **Next question**, type an answer, then **Done answering** and **Finish
   and see report**. The report shows recorded input and simulated reactions.
   The launcher speeds classroom ticks to three seconds; question text/order can
   vary with timing. Typed-input pace is not measured speaking ability. Room
   percentages and answer verdicts come from the fake model.

   > A neural network makes a prediction from an input such as a photo. If it predicts cat when the label is dog, we compare its prediction with the target and calculate a loss. Backpropagation uses the chain rule to trace how each weight contributed to this loss. We then adjust the weights a little in the direction that reduces the error. This is a rehearsal example, not a record from a real class.

   Example answer: “The input is a photo represented as numbers, such as pixel
   brightness. The network combines these numbers with weights to predict a
   label. Input and prediction are different parts of the process.”

2. **1:30–2:30 · Sources and scope.** Use the header's **Policy Lab** button.
   Search **WCAG digital accessibility**. Show the TDRA source's scope, locator
   and limits. It does not automatically govern every private university.
   **UAEU example + general references** adds institutional examples; keep
   **General university context** for the main demonstration. Under **Review a
   question**, enter: “Our university rehearsal website needs captions and
   keyboard access. Does citing WCAG establish that our private university is
   compliant?” The **Deterministic review** surfaces the scoped TDRA reference
   and applicability checks. It does not answer with legal certification.

3. **2:30–3:30 · Uneven information.** Select **Practice a scenario** →
   **Captions fail before a workshop** → **Start scenario**. Stage 1 shows the
   service failure. Change **View as** from Teacher / TA to Privacy and show the
   additional fact about an attendee's identity. Return to Teacher / TA.
   These are functional role views; they do not authenticate different users or
   establish a regulator's mandate. Click **View role proposals**. All three
   scripted selections are labeled **Offline test**; model details identify
   `scripted-demo`. Source details retain scope and verification limits.

4. **3:30–4:45 · Coordination and human ownership.** Click **Reveal next stage**.
   The vendor alternative and unchecked terms now appear. Click **View role
   proposals**. The teacher's proposed vendor route depends on a privacy terms
   check and accessibility confirmation. Show the **Conditional plan**, owners
   and handoffs. Each action still awaits human confirmation; the app executes
   none of them. Select the released vendor-terms fact and record: “Pause the
   vendor route until processing terms are checked and the attendee confirms a
   usable alternative. The teacher retains the final decision.” Click **View
   role activity** to show the stage, decision and fact ID `cf-2b`.

5. **4:45–5:30 · Final update and domain gap.** Reveal Stage 3. It asks for an
   owned, testable fallback plan. Select its new facts and record a human plan:
   “Assign the teaching lead to communication, the privacy contact to vendor
   terms, and the accessibility contact to privately confirm a usable fallback.
   Test it before the next workshop.” Review role activity again. The current
   scripted action catalog reuses stage-2 choices at stage 3; the human decision
   captures this new plan. Do not describe it as generated model reasoning.
   The education gap is operational: who owns an accessible fallback when
   access, privacy and teaching continuity compete? Compare global guidance as
   examples, then check the institution's actual rules.

6. **5:30–6:00 · Evidence and limits.** Show the local report draft, requirements
   mapping and KB manifests listed below. Explain that the later protocol has
   offline verification only. Separately recorded live run 2 accepted 24/27 role
   response contracts, with 6/9 complete stage snapshots; this is structural
   validation, not a legal, citation-quality or learning-outcome score.

## Official deliverables and current gaps

The [official event page](https://aiforgood.itu.int/event/ai-for-good-sandbox-hackathon-united-arab-emirates/?topic=485),
checked 4 November 2026, lists a maximum five-page report, GitHub repository and
knowledge base, plus an optional initial demo video of at most seven minutes
(required for shortlisted teams). Submission is listed as 10 November 2026;
no cutoff time or timezone is stated there.

| Required evidence | Available locally | Still needed |
|---|---|---|
| Use case, requirements, Y.3172 and Readiness 2.0 mapping | [Report draft](ai-for-good-report-draft.md), [engineering mapping](ai-for-good.md) | Confirm team/contact details; render and inspect the official template within five pages |
| Demonstrable agent application and staged incidents | Classroom, three scenarios, role-isolated prompts, conditional plan, human decisions/audit | Expert assessment of source relevance and proposals; the offline script is presentation evidence, not live agent capability |
| Repository | Isolated `codex/yaplab-ai-for-good` branch; MIT code and separate TalkMoves terms retained | User-approved repository URL/access and publication choice; no push or publication performed |
| Knowledge base | `knowledge-base/itu-reference/general` (10 documents/29 chunks) and `uaeu` (13/38), verified manifests and notebook-style chunks | Organiser's accepted format, credentials/access and hosted-ingestion procedure; no hosted import, embedding index or full legal ingestion completed |
| Demo video | This timed walkthrough; local browser smoke below | User decision on recording/delivery; no video recorded or uploaded |
| Transparent audit | Stage/role, released fact and policy references, validation mode, concise decisions and prompt digest | Confirm organiser accepts decision summaries/evidence traces; no private chain-of-thought requested or exposed |

Ask the organiser for the final submission form/destination, exact deadline time
and timezone, team-information sheet, sandbox access and KB import contract.
Also clarify any expectation for model fine-tuning/cloud credits versus the
existing inference prototype. The public instructions mention these resources;
this project has not fine-tuned a model or used an ITU sandbox account.

Source work remains selective: current full PDPL text, cross-border conditions,
institutional applicability and legal approval are not verified. The current
corpus distinguishes UAE policy, non-binding guidance, school-only context and
UAEU student/staff scope. These limits are visible in the product and KB.

## Local evidence

On 4 November 2026 the presenter path above was exercised in a browser against
loopback API/frontend processes: typed lesson → queued question → typed answer →
backend report → Policy Lab source search/review → caption exercise, role switch,
all three coordination stages → human decision → role activity. The stage-2
screen showed the two prerequisite handoffs and a recorded decision with `cf-2b`.
This was **offline scripted software verification**; no paid provider requests,
real classroom records, external uploads or submission occurred.

The WCAG question exposed a retrieval-priority issue during the walkthrough. It
was fixed with a scoped regression check before the final browser recheck.
Required offline suites and current counts are recorded in
[the demo evidence](evidence/ai-for-good-demo-2026-11-04.json). Earlier immutable
live-result files remain separate. The report still needs pagination/rendering
in a supported Documents runtime; see [the rendering handoff](ai-for-good-rendering-handoff.md).
