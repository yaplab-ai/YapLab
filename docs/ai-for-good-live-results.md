# Approved Nebius coordination evaluation

One user-approved run on 4 November 2026 evaluated the unchanged `f021dd1`
coordination protocol using the existing Nebius credential. It sent the reviewed
synthetic facts, project-authored role instructions/catalogs and public-policy
paraphrases to `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`. It did not send real student
data, transcripts, audio, slides or repository files. The original application
provider/configuration was not changed. No provider switch, retry or fallback
was used; the 27-request allowance has been consumed.

## Observed result

| Measure | Observed |
| --- | --- |
| Attempted requests / provider responses | 27 / 27 |
| Role responses accepted by schema and allowed-ID checks | 14 of 27 |
| Rejected role responses | 13, all labelled `invalid_response` |
| Snapshots with all three role responses accepted | 1 of 9 |
| Provider-reported input / output tokens | 26,604 / 3,289 |
| Largest reported output | 196 tokens, below the requested 400-token cap |
| Provider finish reasons | All 27 `stop`; no reported length truncation |
| Reported request latency | Median 2.624 s; maximum 3.192 s |
| Missing usage records | 0 |
| Cost calculated from reported usage and list prices | $0.0023856 USD |
| Verified invoice charge | Unknown; no billing-account lookup was performed |

| Scenario | Stage 1 accepted roles | Stage 2 accepted roles | Stage 3 accepted roles |
| --- | --- | --- | --- |
| Transcript disclosure | 2 / 3 | 2 / 3 | 1 / 3 |
| Caption failure | 2 / 3 | 1 / 3 | 1 / 3 |
| Practice feedback mistaken for grade | 2 / 3 | 0 / 3 | 3 / 3 |

The cost calculation uses the published $0.06/million input and $0.24/million
output list rates: `(26604 * 0.06 + 3289 * 0.24) / 1,000,000`. It assumes no
cache discount and is not an invoice, a balance check or an account-price
verification. See the [Nebius model/pricing page](https://nebius.com/services/token-factory/models/nvidia-nemotron-models-inference).
The earlier $0.018309 dry-run estimate used a deliberately generous token proxy;
the $0.10 planning envelope was not a provider-enforced spending limit.

## Interpretation and remaining work

Provider access and the exact model alias worked for this run. The prototype
rejected invalid responses instead of displaying their proposals; those roles
remain unavailable. The model did not meet the all-role structural acceptance
criterion. Fourteen accepted responses are not evidence of policy accuracy,
correct institutional mandates or educational benefit. Semantic quality remains
unreviewed, and this small hand-authored set is not a representative benchmark.

The current audit reports only the coarse `invalid_response` category. Raw
completions were intentionally not retained, so the thirteen rejection causes
cannot be reconstructed as JSON/schema versus invalid/duplicate action, fact,
source or question IDs. Provider finish reasons and output counts give no
evidence of truncation. Do not invent a more specific diagnosis. The useful next
local step is safe validation-category telemetry and clearer output constraints,
with offline regressions before another approved provider comparison.

A read-only offline recheck matched all 27 prompt hashes and evidence snapshots
to the prepared requests, verified the 27 unique scenario/stage/role usage
records, and revalidated all 14 accepted responses' allowed IDs. The saved
[live evidence](evidence/ai-for-good-coordination-live-2026-11-04.json) contains
synthetic/public source notes, validated IDs, hashes and redacted telemetry;
no keys, private reasoning or raw completions are stored. Its overall structural
result is `fail`, with `evaluation_complete=true`.

The billing owner, balance, contract and organisation-level retention settings
remain unverified, as disclosed and accepted for this bounded run. No settings,
infrastructure or credentials were created or changed. Further paid calls or a
Claude/OpenAI comparison need a concrete scope/cost report and any required
authorization; none was attempted. Hosted KB import, submission destination,
expert review and final report rendering remain separate dependencies.


The subsequent [offline diagnostic follow-up](ai-for-good-validation-diagnostics.md)
implements fixed categories and a clearer protocol-2 prompt contract. The original
live evidence remains unchanged; no rejected raw completion was recovered or
assigned a new cause, and no further provider call was made.
