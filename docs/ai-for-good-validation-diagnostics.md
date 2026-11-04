# Response validation diagnostics and protocol 2

This increment is entirely offline. It preserves the original protocol-1
[live evidence](evidence/ai-for-good-coordination-live-2026-11-04.json), its
14 accepted/13 rejected responses, and the [protocol-1 plan](evidence/ai-for-good-coordination-plan.json).
No additional provider request, charge, credential operation or provider switch
was performed. Protocol 2 has no live adherence or semantic-quality result yet.

## Findings supported by inspection and reproduction

| Finding | Evidence and scope | Repair |
| --- | --- | --- |
| The prompt omitted the uniqueness rules that validation already required | Offline fixtures reproduce rejection of duplicate action, fact, source and question IDs; the old prompt did not state those rules | State uniqueness and empty-array rules explicitly; supply exact role-scoped allowed IDs and a matching response schema |
| Duplicate JSON object keys silently overwrote earlier values | A protocol-1 response with two `questions` keys accepted the last value | Reject duplicate keys at every nesting level before schema validation |
| Provider `ValueError`/`TypeError` could be labelled `invalid_response` | Offline clients raising those errors before returning content reproduced the label | Separate provider invocation, known response failures and unexpected validator defects |
| Detailed rejection causes were unavailable | The saved live evidence has only the coarse category; raw completions were not retained | Record fixed validation categories for future runs without rejected values or exception text |

The saved run has 27 linked provider-success events, so its 13 rejections occurred
downstream of returned content. Their exact causes cannot be reconstructed. The
new duplicate-ID, formatting and schema fixtures are candidate failure modes,
not diagnoses of those thirteen responses. The provider-exception bug is a
general classification defect, not evidence that it occurred in that saved run.

## Privacy and failure boundaries

Only the fixed `validation_issue` label is persisted with an unavailable role
whose reason is `invalid_response`. The labels are:

| Family | Fixed labels |
| --- | --- |
| Response boundary | `non_text_response`, `response_too_large` |
| JSON parser | `json_syntax`, `duplicate_json_keys`, `nonfinite_json_value`, `json_number_limit` |
| Schema | `schema_extra_fields`, `schema_missing_fields`, `schema_types`, `schema_limits`, `schema_contract` |
| Duplicate IDs | `duplicate_action_ids`, `duplicate_fact_ids`, `duplicate_source_ids`, `duplicate_question_ids` |
| Unknown IDs | `unknown_action_id`, `unknown_fact_id`, `unknown_source_id`, `unknown_question_id` |

The first applicable category is recorded; it is not an exhaustive error trace.
Pydantic error text, locations, context, model-supplied keys/values, raw
completions and private reasoning are never diagnostic fields. Non-standard
NaN/Infinity literals are rejected. Numeric literals exceeding the local parser's
4,096-character or float-representation limits receive `json_number_limit`;
ordinary numbers are still rejected by the string/container response schema.
These bounds also prevent parser failures from being mislabelled internal errors.

Provider exceptions become `provider_error`. Unexpected validator exceptions
become `validation_error`, without a fabricated model-response category. Neither
stores exception text. The store rejects unknown categories or a category on an
inconsistent role status/reason. A role audit exposes only that role's category.
Older results without a category remain readable and receive no inferred label.

## Prompt and schema changes

Protocol 2 gives each role explicit `allowed_ids`, `response_schema` and a valid
`empty_response`, alongside its existing released facts, mandate and policy
notes. The schema specifies required fields, closed objects, array limits,
string enums and unique fact/source/question arrays. The prompt separately states
one proposal per action ID, which is also enforced locally. Empty proposals and
questions remain valid abstention; unsupported IDs still fail rather than being
repaired or matched approximately.

The application still sends the provider's JSON-object response format. The
schema is **prompt context**, not verified provider-side structured-output
enforcement. No SDK response-format, output cap, retry, fallback or provider was
changed. The protocol version and prompt hashes changed, so comparison must use
the separately prepared [protocol-2 plan](evidence/ai-for-good-coordination-plan-v2.json).

Offline tests check both scopes across all three scenarios/stages, including
role/future-fact isolation in schema enums. They also reconstruct the fourteen
saved accepted selections and confirm their IDs remain allowed. This does not
retest their discarded original JSON under the stricter parser or establish
better model adherence.

## Evaluation records

Future evaluation summaries retain only allowlisted diagnostic categories and
bounded telemetry: known finish/error enums, latency, token counters and
scenario/stage/role IDs. They distinguish attempted calls, provider responses,
completed snapshots and structural acceptance. Known list-price usage is derived
from the plan's rates; incomplete usage never becomes a verified total invoice.

The harness stops subsequent snapshots after provider/internal failures, missing
usage, a reported output above 400 tokens or known list-price usage reaching the
planning budget. These are post-snapshot checks; already accepted requests can
still be billed. They do not enforce an account dollar cap. Checkpoints record
in-flight state so interruption does not imply that no call occurred. Each uses
a same-directory temporary file, file flush/fsync, atomic replacement and a
directory fsync; a pre-replacement failure preserves the prior checkpoint. A
directory-sync failure after replacement leaves durability uncertain and stops
the run. Checkpoint
write failures stop further calls and produce only a sanitized local recovery
record. Historical evidence is never rewritten by the default dry run.

## Proposed next experiment — not authorised or run

Run the same 27 scenario/stage/role requests on Nebius's
`nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`, changing only the protocol-2 prompt
contract and diagnostic instrumentation. Keep the 400-output-token limit,
no retries/fallback, the same synthetic facts and public policy summaries,
and the default-disabled application setting. This avoids a provider switch
confounding the first comparison. Report category counts, abstention, conflicts,
per-role and all-role structural acceptance, usage and any stop condition.

The new dry plan measures **165,754 prompt UTF-8 bytes**. Its generous proxy is
359,156 input tokens plus at most 10,800 output tokens, yielding **$0.02414136 USD**
at the recorded $0.06/M input and $0.24/M output rates. This is a planning
estimate, not tokenizer output, a current account quote or a billing guarantee.
Recheck applicable prices and obtain separate authorization before making any
call. Billing-owner/retention uncertainty and the $0.10 non-enforced envelope
remain disclosed. A Claude/OpenAI comparison would require its own adapter,
scope and pricing review; none was attempted.


## Verification and command status

The final local pass completed **90 existing backend checks**, **69 policy-related
unit tests** (14 policy, 6 export, 11 coordination, 8 coordination HTTP, 19
evaluation and 11 adversarial diagnostic tests), the standalone staged-scenario
checks, **97 frontend tests**, the frontend production build and offline API
wheel/sdist builds. An extracted-wheel smoke test verified the packaged taxonomy,
duplicate-key rejection, role audit and disabled-by-default endpoint. No provider
calls or new charges were made by this increment.

The independent reviewer reran parser/privacy cases and the checkpoint/CLI
reproductions after the fixes. Failure-injection tests cover interrupted writes,
file/directory sync and replace failures, prior-checkpoint preservation and no
further simulated calls after checkpoint failure. CLI statuses are:

- `0`: dry run, or a live evaluation completed with all structural checks passing.
- `2`: live evaluation completed but structural validation failed.
- `1`: live evaluation stopped/incomplete or checkpoint failure.

Argument-validation errors also use argparse status `2`, with a usage message.
A completed structural pass still says nothing about legal/educational quality.
The frontend retains its existing non-failing HMR port and large-chunk warnings;
the API sdist retains its existing missing-standalone-README warning.
