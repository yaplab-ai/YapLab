# Live video v3 and local demonstration — 6 November 2026

The v3 video shows Policy Lab running live on Nemotron 3 Nano via Nebius through
the real UI. Prompt 12 identifies exercise `I2STSl3jQfrC85AziqmvLp84vBKtDUi_` as
the video take. Its two exact timeline exports, plus the discarded first take,
are archived with hashes in [the live-demo evidence directory](evidence/ai-for-good-live-demo-2026-11-06/README.md).
The timelines contain saved model outputs and decision text; video-take identity and
the recording-script authorship are reported by the brief, not independently
established by those files. No video was recorded or edited for this launcher change.

## Launch the live mode shown in the setup scene

```bash
cd /Users/zukhriddin/Documents/HackathonProjects/YapLab-ai-for-good
NEBIUS_API_KEY='<your-key>' python3 scripts/run-hackathon-demo.py --live
```

With the key already exported or in this checkout's root `.env`, the command is
simply `python3 scripts/run-hackathon-demo.py --live`. Open the printed local URL,
then **Policy Lab**. Each **View role proposals** can make up to three paid model
requests. The server-side policy coordination cap defaults to 27; set
`--max-model-calls N` for 1–60. The recording's manual configuration used 36 and its
two takes consumed 18 requests; the new default remains 27. The cap resets on API
process restart and is not an account-level dollar cap.

TTS and STT providers are off. For a classroom demonstration use typed input and
turn camera and voices off in Setup; the live classroom's configured LLM calls
are separate from, and outside, this policy coordination cap. Policy Lab uses
the direct provider; existing classroom fallback behavior is unchanged. Keep all
inputs synthetic. Starting another live session can produce different answers
and new charges; the saved session is not a script for future model behavior.

The existing hybrid auto-detection is unchanged: complete cached vector assets
are enabled unless explicit settings were supplied, and startup probes print
the actual mode for general/UAEU search. See [exact hybrid setup](ai-for-good-local-kb.md#record-with-hybrid-retrieval).
`--live` and `--replay-live` are mutually exclusive. Ctrl+C stops the launcher's
own API/UI processes; use distinct free ports when another agent is working.

## On-screen sequence in video v3

1. **Search.** Show the caption/accessibility source results, actual retrieval
   mode, jurisdiction, scope and verification limits. The selective corpus does
   not establish full statutory coverage or institutional applicability.
2. **Stage 1 role views.** Open caption failure and switch teacher, privacy and
   accessibility views to show their different released facts.
3. **Live proposals.** Use **View role proposals**, show model-written, unverified
   stated rationales, and keep the stage 1 teacher's **partial** result visible.
   The saved issue is `duplicate_action_ids`; provider success does not mean a
   fully accepted answer, source entailment or legal correctness.
4. **Plan and model details.** Show conditional ownership/handoffs and the
   configured Nemotron 3 Nano / Nebius / protocol 4 details. A proposed check is
   not evidence that a person performed it; no workshop action executes.
5. **Stage 2 and decision.** Reveal the vendor-terms facts, inspect the role
   outputs and record the vendor-terms decision with fact `cf-2b`. The decision
   in this video was synthetic text entered by the recording script, not an
   observed educator decision.
6. **Stage 3 and candidate gaps.** Reveal the final facts, inspect the conditional
   plan and candidate operational gaps, including reviewed UAE scope, scoped
   global examples and institutional/vendor/usability evidence still needed.
   These are questions for review, not demonstrated national-law deficiencies.
7. **Audit timeline.** Show progressive releases, actual per-request latency,
   reported tokens, validation, plans and the synthetic decision's evidence
   reference. JSON/HTML exports preserve saved modes and integrity hashes;
   hashes do not establish institutional authority or independent provenance.

The archived session has 18 provider-success records, 35,350 input/2,557 output
tokens, estimated $0.00273468 at recorded list prices, invoice unverified. Sixteen
roles were completed and two partial; the other partial is stage 3 privacy in the
first take, discarded because its header showed the offline badge. The archive
attributes approval `user-approved-2026-11-06-video-live-36` to the source brief.
This live UI demo is **not part of the scored evaluation** and establishes no
educational benefit. The scored run remains 5 November: 26 fully accepted roles,
one partial, and frozen-rubric 8 match/15 partial/4 miss, with unsupported model
claims retained in [the results](ai-for-good-v4-results.md).

## Offline convenience and recorded replay

No key? Run `python3 scripts/run-hackathon-demo.py` without `--live` for the fake
classroom and scripted role answers, with no model or speech-provider calls.
To inspect the actual 5 November scored run without new model calls:

```bash
python3 scripts/run-hackathon-demo.py --replay-live docs/evidence/ai-for-good-protocol4-live-2026-11-05/caption-failure.json
```

Stop the live launcher first, or use separate free ports. The preserved earlier
walkthrough below explains all three scored replays and their limitations; it
is distinct from the live v3 sequence above.

## Earlier 5 November scored-run replay walkthrough

**5 November 2026.** The actual app run and all three saved replays are available.
This earlier route prepared the separate video; no new video was recorded or edited by this engineering task.
The official initial demo is optional, at most seven minutes; shortlisting makes
it required. Keep scripted classroom footage and recorded live policy evidence
clearly labelled.

### Exact commands

From the isolated checkout:

```bash
cd /Users/zukhriddin/Documents/HackathonProjects/YapLab-ai-for-good
python3 scripts/run-hackathon-demo.py
```

Ctrl+C stops that launcher and its children. Then open the main recording:

```bash
python3 scripts/run-hackathon-demo.py --replay-live docs/evidence/ai-for-good-protocol4-live-2026-11-05/caption-failure.json
```

For other scenarios, substitute `transcript-disclosure.json` or
`feedback-as-grade.json` in that same directory. Run one launcher at a time on
default API 8765/UI 5179. Use `--api-port`/`--ui-port` for distinct free ports when
another agent is working; do not stop their process.

Without `--live`, the launcher sets fake classroom, scripted policy generation, speech providers
off and camera/audio off. Replay opens Policy Lab directly and offers no advance,
generate or decision controls. Its saved outputs remain the real Nebius run;
reopening the page makes **no new model-provider calls**.

Cached local vector assets are auto-enabled when present, unless explicit
`FRONTROW_POLICY_VECTOR_*` values were supplied. Startup probes and prints actual
`general: hybrid` / `uaeu: hybrid` (or lexical/unknown). See
[exact hybrid setup](ai-for-good-local-kb.md#record-with-hybrid-retrieval).
The replay preserves the run's saved source choices; startup search probes do not
recompute or alter those choices.

### Suggested six-minute route

1. **0:00–0:50 — classroom, offline.** Use the demo deck and typed synthetic
   explanation, take a scripted Q&A question, then finish and show the report.
   Typed timing and scripted reactions are not measured speaking or learning
   results. Retain the separate TalkMoves notice.
2. **0:50–1:25 — references, offline.** Open Policy Lab:22 general references,
   with three explicitly UAEU-only examples. Search captions/live media; show
   the actual Hybrid/Lexical label, source scope and verification limits. This
   is a selective source corpus, not full statutory coverage.
3. **1:25–3:15 — caption replay.** Switch launchers. Show the dated banner:
   `Recorded live run · 2026-11-05 · Nemotron 3 Nano via Nebius · protocol 4 · no new model calls`.
   Scroll through the three saved stages. Each role has actual model-written,
   unverified rationales. In stage 2 privacy proposes identity protection and
   omits vendor-terms verification; the teacher's vendor-resumption plan shows
   **missing prerequisites**, with privacy/accessibility handoffs. Stage3 has
   both prerequisite actions, so it becomes **awaiting human confirmation**.
   No workshop action executes.
4. **3:15–4:20 — timeline and gap.** Show actual request tokens/latency and
   validation in Audit timeline, synthetic facilitator decision labels, exact
   evidence IDs and JSON/HTML exports. Then show the caption candidate-gap
   panel: reviewed UAE scope, global comparison and institution/vendor/usability
   evidence still needed. This is a candidate operational question, not a
   national-law defect.
5. **4:20–5:15 — show a real limitation.** Open feedback replay:stage 3 teacher
   is **partial**, with one retained question and no proposal; timeline issue
   is `schema limits`. Sources/details in stage 1 show two `rationale_rejected`
   omissions (`rationale_length`, `rationale_markdown`). An accepted stage 3
   accessibility rationale names an unsupported “EQA team”/“Al-Qasimi policy”:
   explicitly acknowledge that structural validation is not factual verification.
   Transcript replay also has two screened legal-term rationale omissions.
6. **5:15–6:00 — expected versus actual.** Show the frozen team-authored rubric
   and [saved per-row comparison](evidence/ai-for-good-protocol4-live-2026-11-05/expected-actual.md).
   Transcript0/7/2, caption 4/4/1, feedback 4/4/1 match/partial/miss: total 8/15/4.
   All 27 provider responses succeeded, but only26 roles were fully structurally
   accepted, one partial. Exact list-price estimate $0.00420348, invoice unverified.
   The retrieval benchmark improved top-three coverage, not MRR or all abstentions;
   it also uses provisional team labels.

### Browser evidence and limits

All three actual exports were browser-verified:banner, proposals/rationales,
three plans, ordered timeline and candidate gaps. The four omission labels and
partial feedback result were inspected where they occurred. No wholly unavailable
role occurred in this run; do not stage one for the video.

[Caption prerequisite screenshot](evidence/ai-for-good-protocol4-live-2026-11-05/replay-caption-prerequisite.jpg)
and [partial feedback screenshot](evidence/ai-for-good-protocol4-live-2026-11-05/replay-feedback-partial.jpg)
show useful recording moments. The no-flag classroom/policy generation remains
scripted; `--live` uses configured Nebius calls. Historical protocol3 is not this app run. Hashes establish integrity,
not institutional authority. See [actual results and substantive limits](ai-for-good-v4-results.md).
