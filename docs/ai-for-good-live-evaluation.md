# Synthetic coordination evaluation

The default evaluation is **offline**: it prepares role requests from the three bundled synthetic scenarios at each of their three stages, using the same released-fact snapshots and request preparation as the application. It reports 27 planned requests (three roles per stage), actual system-plus-user UTF-8 byte counts, a planning token proxy and a cost estimate. It does not read human decisions, transcripts, environment files or credentials, call a provider, or assess semantic quality.

From `apps/api`:

```sh
.venv/bin/python scripts/evaluate_coordination.py
# Optional new local file; an existing file is never overwritten:
.venv/bin/python scripts/evaluate_coordination.py --output /path/to/new-dry-run.json
```

The planning input envelope is twice the observed prompt UTF-8 byte count plus 1,024 tokens per request. This is a deliberately generous proxy, **not a tokenizer count or a guaranteed bound**: tokenization, provider message framing and prices can differ. The request limit is 400 output tokens, at most 10,800 output tokens across 27 calls. The estimate uses the published Nano prices of $0.06 per million input and $0.24 per million output tokens, recorded as of 2026-11-04, against a $0.10 planning envelope. These are estimates, not a billing guarantee or a hard spend cap. The explicit hard limits are 27 attempted calls and 400 output tokens per request. See the [Nebius NVIDIA model and pricing page](https://nebius.com/services/token-factory/models/nvidia-nemotron-models-inference); verify current terms and prices before any live run.

## Separately authorized live evaluation

**Do not run this command without separate explicit authorization for the provider calls and charges.** Nebius is an explicitly selected alternative evaluation provider; its selection here does not establish that it is the configured application provider. No provider call is needed to use the dry run.

After obtaining authorization, choose a non-sensitive identifier for it and set `NEBIUS_API_KEY` in the process environment through an appropriate secure mechanism. Do not put a key in a command, file, or approval reference. Install the project's optional OpenAI-compatible SDK if needed. Then, from `apps/api`, use a new output path:

```sh
.venv/bin/python scripts/evaluate_coordination.py \
  --execute-live --provider nebius \
  --model nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B \
  --approval-reference APPROVAL-ID \
  --output /path/to/new-live-result.json
```

The approval reference is recorded as supplied; its presence does not prove that permission was granted. The explicit live flag, provider, model allowlist and reference are all required. No `.env` is loaded by the harness. The existing direct Nebius `OpenAIClient` sends the fast-tier requests with a 400-token maximum and SDK retries disabled; this harness adds a 27-attempt cap, uses no fallback and submits only the bundled synthetic facts and curated policy notes. The $0.10 estimate gate is a planning check, not an enforced billing limit. Cancellation or unavailable provider usage can leave actual costs unknown.

The result contains the approval reference, scenario/stage/role identifiers, protocol and corpus versions, provider/model, prompt hashes and attempt flags, curated source metadata and hashes, validated proposal and evidence IDs, structural status, dependency status, and bounded usage counters when reported. Hashes pin the supplied notes and exact prepared prompts; they do not establish legal authority. It does not save prompts, raw completions, private model reasoning, credentials, human decisions or transcripts. A structural pass means every role returned a response accepted by the application's existing schema and ID checks. Empty but valid proposals can pass structurally; this is not a judgment that proposals are useful, appropriate, legally correct or educationally effective. Semantic quality remains **unreviewed** until a human assesses it. Provider errors, timeouts and invalid responses are structural failures, not proof of an educational outcome.

## Provider data handling

The account's zero-data-retention setting is unknown; the harness neither checks nor changes it. Nebius's [legal quick guide](https://docs.tokenfactory.nebius.com/legal/legal-quick-guide) describes organization-level ZDR, its default retention and dynamic processing locations, and states that content is not used for model training. The binding [Token Factory supplemental terms](https://docs.nebius.com/legal/token-factory) also permit processing inputs and outputs to train smaller speculative-decoding models in circumstances described there; the quick guide says its summary does not replace the governing terms. Review the applicable agreement and any account settings rather than assuming the guide resolves that difference. ZDR does not necessarily cover service metadata; verify the current applicable terms and [DPA](https://docs.nebius.com/legal/dpa), including processing location, before sharing any sensitive data. This evaluation uses synthetic data only and does not establish legal compliance or learning gains.

## Local configuration observed

The original local configuration was observed with `FRONTROW_LLM=anthropic` and no model override; the application default resolves to `claude-haiku-5-5`. Only the presence of Anthropic and Nebius credentials was checked, not their values. The isolated worktree had no `.env` and policy model calls were off. The current coordination adapter does not support Anthropic because its adapter requests up to 1,024 output tokens; the separately gated Nebius evaluation is an explicit alternative using an existing credential, not an automatic application provider change. Remote account access and model availability have not been verified.


## Concrete approval scope and billing uncertainty

The proposed target is Nebius Token Factory's public OpenAI-compatible
`https://api.tokenfactory.nebius.com/v1/chat/completions` endpoint, model
`nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`. This exact API ID and this account's access
have not been checked against an authenticated catalog. A failure must be recorded;
the harness must not silently substitute another model/provider or create an
endpoint. The original app's Anthropic configuration remains unchanged.

Prompt content is synthetic and includes **project-authored** role instructions,
fictional scenario text and action/question catalogs, plus public-policy
paraphrases. Those unpublished project prompts are content disclosed to Nebius;
the evaluation does not upload repository/source files. Each request contains:

- A system instruction with the response schema and evidence/role boundaries.
- A user JSON object containing role, mandate, scenario ID, stage, institution,
  corpus/protocol versions, released fact IDs/text, allowed action/question
  IDs/text, and retrieved policy notes (ID, title, authority, official URL,
  jurisdiction, document type, scope, summary, limitations and institution).
- The model ID, JSON response format, 400-output-token limit and
  `chat_template_kwargs.enable_thinking=false`. The client timeout is eight seconds.

No human decision text, real student information, lesson transcripts, slides,
audio, emails, raw policy PDFs, Git history or environment files enter prompts.
The API key goes to the intended provider as an authentication header, never as
prompt text or a saved result. Normal service/network metadata, including IP
address and request/account billing metadata, can also reach the provider.
The exact 27 proposed request bodies were prepared locally, without credentials
or network calls, in `/tmp/yaplab-coordination-proposed-requests.json`; prompt
fingerprints match the committed dry-run plan. This preview is a temporary local
review artifact, not a submitted or uploaded file.

Billing would use the Nebius organisation/account associated with the existing
`NEBIUS_API_KEY` found in the original checkout. **The account/organisation name,
project, billing owner, balance, applicable contract and ZDR status are unknown.**
Key presence does not identify or authorise a billing account. No authenticated
billing lookup, balance check or service call was made, and no new credential,
subscription or infrastructure was created. Confirm the intended billing account
before approving use of that credential.

Approval can be limited to this model/provider, the previewed synthetic/public
policy/project-prompt content, one evaluation, at most 27 attempted calls and
400 output tokens each, without retries, fallback, deployment, sharing or
submission. The current planning estimate is **$0.018309 USD**: a 261,950-input-token
proxy at $0.06/million plus at most 10,800 output tokens at $0.24/million. It
assumes no cache discount and excludes taxes/account-specific pricing.

The proposed $0.10 envelope is **not an enforceable account spending cap**.
The harness stops before execution when its estimate exceeds that envelope,
but input tokenization and billing remain provider-controlled; calls already
accepted may be billed after cancellation and usage may be missing. A strict
dollar ceiling requires a confirmed provider-side control or separately agreed
treatment of that uncertainty. No such account setting has been changed. The
live run remains pending explicit approval of charges, content disclosure and
the intended billing account; it has not been denied or attempted.
