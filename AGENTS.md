# YapLab project instructions

- Product name: **YapLab**. Keep the existing `frontrow` Python package and
  `FRONTROW_*` settings unless a migration is explicitly needed.
- Use **GPT-6.1 Sol**, reasoning effort **extra high (`xhigh`)**, for the main
  engineering/orchestration thread. Use **GPT-6.1 Terra**, **extra high (`xhigh`)**,
  for delegated subagents. These are development-agent preferences, not runtime
  model requirements for the YapLab application.
- Inspect uncommitted work before editing. Preserve teammates' work and existing
  rehearsal, voice, and report behavior. Do not reset or overwrite other changes.
- The AI for Good UAE work targets English-language rehearsal by university
  teachers and teaching assistants. UAE policies are a reference case; identify
  education-domain gaps and compare relevant global examples with explicit scope.
- Cite primary sources. Distinguish law, guidance, proposals, implementation,
  offline tests, live-provider evidence, and real educational outcomes. Never
  describe a prototype review as legal certification or a measured learning gain.
- Policy exercises use synthetic data. Audit records contain evidence references,
  concise decision summaries, and review modes; do not solicit private model
  chain-of-thought.
- Do not publish, deploy, share, submit, purchase services, or change external
  infrastructure without the user's explicit authorization. Local implementation
  and offline testing are authorized.
- Preserve the MIT code license and TalkMoves artifacts' separate
  CC BY-NC-SA 4.0 restrictions.

## Local verification

From `apps/api`, run `.venv/bin/python verify.py` with `FRONTROW_LLM=fake`,
`FRONTROW_TTS=none`, and `FRONTROW_STT=none`. Run policy verification scripts
separately as documented in `docs/ai-for-good.md`.

From `frontend`, run `npm run test:live` and `npm run build`.
