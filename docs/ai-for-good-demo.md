# Recording guide — approved protocol-4 evidence

**5 November 2026.** The actual app run and all three saved replays are available.
This guide prepares the separate video; no new video was recorded or edited here.
The official initial demo is optional, at most seven minutes; shortlisting makes
it required. Keep scripted classroom footage and recorded live policy evidence
clearly labelled.

## Exact commands

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

The launcher sets fake classroom, scripted policy generation, speech providers
off and camera/audio off. Replay opens Policy Lab directly and offers no advance,
generate or decision controls. Its saved outputs remain the real Nebius run;
reopening the page makes **no new model-provider calls**.

Cached local vector assets are auto-enabled when present, unless explicit
`FRONTROW_POLICY_VECTOR_*` values were supplied. Startup probes and prints actual
`general: hybrid` / `uaeu: hybrid` (or lexical/unknown). See
[exact hybrid setup](ai-for-good-local-kb.md#record-with-hybrid-retrieval).
The replay preserves the run's saved source choices; startup search probes do not
recompute or alter those choices.

## Suggested six-minute route

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

## Browser evidence and limits

All three actual exports were browser-verified:banner, proposals/rationales,
three plans, ordered timeline and candidate gaps. The four omission labels and
partial feedback result were inspected where they occurred. No wholly unavailable
role occurred in this run; do not stage one for the video.

[Caption prerequisite screenshot](evidence/ai-for-good-protocol4-live-2026-11-05/replay-caption-prerequisite.jpg)
and [partial feedback screenshot](evidence/ai-for-good-protocol4-live-2026-11-05/replay-feedback-partial.jpg)
show useful recording moments. The default classroom/policy generation remains
scripted. Historical protocol3 is not this app run. Hashes establish integrity,
not institutional authority. See [actual results and substantive limits](ai-for-good-v4-results.md).
