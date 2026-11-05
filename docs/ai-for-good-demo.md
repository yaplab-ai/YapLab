# Recording guide for the final-push build

**5 November 2026.** Record from this build after code freeze. Video production
is separate; this guide does not claim that a new video exists. The official
initial video is optional, at most seven minutes; shortlisting makes it required.

## Launch the offline demo

```bash
python3 scripts/run-hackathon-demo.py
```

Use `--api-port` and `--ui-port` if the defaults are occupied; do not stop another
agent's server. The launcher sets fake classroom, scripted policy proposals,
no speech providers and camera/audio off by default. It loads no provider key.
Optional hybrid setup is in [the retrieval guide](ai-for-good-retrieval.md);
without it search visibly reports lexical mode.

Suggested six-minute route:

1. **0:00–0:50 — classroom.** Start teaching, keep the demo deck, enter the room
   and type a synthetic explanation. Take a fake Q&A question, type an answer,
   then finish. The report explains that typed timing/scripted reactions are not
   measured speaking or learning results. Retain the separate TalkMoves notice.
2. **0:50–1:35 — sources.** Open Policy Lab. General shows 22 references; UAEU
   explicitly adds three examples. Search captions/live web media. Show the
   actual `Hybrid · lexical + local vectors` or `Lexical` label and the source's
   jurisdiction/scope/verification. Full statutory coverage is not claimed.
3. **1:35–3:15 — staged incident.** Start caption failure as Teacher/TA. Reveal
   one stage at a time; Privacy and Accessibility expose different facts. View
   role proposals at stage 2: they are explicitly Offline test / scripted-demo.
   Rationales say `scripted offline example`; source details link each proposal
   to its own facts and references. The conditional vendor plan requires privacy
   terms and accessible-option confirmation; no action executes.
4. **3:15–4:30 — gap and decision.** At stage 3 show Candidate gaps, reviewed UAE
   sources, scoped global examples and evidence needed. Explain this is a
   higher-education operational hypothesis, not a national-law defect. Select a
   released fact, enter a synthetic facilitator decision and record it.
5. **4:30–5:30 — audit.** Open Audit timeline. Show progressive releases,
   request/validation/plan records, prompt/source digests and the decision's
   evidence reference. Offline request usage is unavailable, not paid inference.
   JSON and self-contained HTML exports preserve modes and hashes.
6. **5:30–6:00 — expected versus actual.** Show the frozen team-authored rubric
   and retrieval benchmark. Be explicit about 3/4 abstentions and hybrid's
   unchanged/worse rank metric. Actual protocol-4 provider comparison remains
   pending approval; do not present scripted output as a live result.

## Replay an actual saved live exercise

The read-only UI/launcher is implemented, but an actual protocol-4 recording is
not yet available because the paid run was denied before execution. After a
permitted run, select one exact scenario export:

```bash
python3 scripts/run-hackathon-demo.py --replay-live /absolute/path/to/protocol4-exercise.json
```

Replay opens Policy Lab directly. The top badge says Recorded live replay, and
the banner identifies date, Nemotron 3 Nano via Nebius, protocol 4 and **no new
model calls**. It displays actual saved proposal/rationale/status/plan/timeline
records and the scenario gap panel. No advance, generate or decision controls
are offered. Do not use offline fixtures or relabel protocol-3 files; those are
rejected by the replay's mode/protocol checks.

## Exact screen changes from the prior recording guide

- Expanded library: 22 general / 25 UAEU sources and corpus `.5`.
- Source search displays the retrieval mode actually used.
- Stated rationale appears under each proposal, with separate live-unverified
  versus scripted-example labels.
- Stage 3 adds the Candidate gaps debrief with explicit comparative scope.
- View audit timeline opens a readable ordered record, with JSON/HTML exports.
- `--replay-live` opens a read-only recorded-exercise screen with an origin/mode
  banner; a hash is an integrity check, not proof of institutional authority.

The browser pass verified classroom → report → hybrid search → caption stages →
scripted rationales → gaps → decision/audit. Actual live replay verification and
expected/actual model footage remain pending. See [current results/status](ai-for-good-v4-results.md).
