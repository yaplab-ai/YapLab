# Local policy retrieval and benchmark

Policy source search defaults to weighted lexical matching, with scope filtering before ranking. It can optionally combine lexical ranks with source ranks aggregated from the prepared MiniLM/FAISS chunk index using reciprocal rank fusion (constant 60). A lexical match is required before vector candidates are considered; this deliberately conservative gate can miss relevant results when wording has no overlap. Neither a match nor a similarity score establishes applicability, legal compliance, implementation, or educational outcomes. Consult the cited source, locator, scope and limitations.

The vector worker is an isolated, offline local process. The API's main environment does not require vector packages. The worker checks bundle integrity against the current corpus, index and metadata hashes, institutional scope, the pinned model revision and its file hashes before use. Configure all three variables to opt in:

```sh
export FRONTROW_POLICY_VECTOR_PYTHON=/tmp/yaplab-vector-venv/bin/python
export FRONTROW_POLICY_VECTOR_MODEL=/tmp/yaplab-vector-model
export FRONTROW_POLICY_VECTOR_INDEX_ROOT=/absolute/path/to/index-root
```

The index root contains `general` and `uaeu` subdirectories built from their respective checked notebook bundles. The index builder requires an output directory that does not already exist. See `vector_policy_kb.py --help` and the local KB documentation for bundle preparation and provenance. The pinned model must already be local; no model download, provider request, or implicit credentials are used. An unavailable, stale, mismatched, invalid, or timed-out vector worker falls back to lexical search. `/policy/search` reports `retrieval_mode` as `hybrid` or `lexical` for the mode actually used; review audit records also report their mode. The gate yields lexical mode when there is no lexical match. The separate process loads the model on each request, so hybrid mode adds startup latency.

`frontrow/policy/retrieval_labels.json` contains 40 team-authored, not expert-validated queries across the three scenarios and four out-of-scope abstention cases. Earlier pre-results label versions are preserved in commits 82e7a61 and f970e64; the final label freeze removed an unavailable source before rankings were inspected. Labels identify some relevant sources, not an exhaustive relevance set. Each positive query can have more than one expected source. Recall@3 averages the fraction of each query's expected sources returned in its top three; MRR averages the reciprocal rank of the first expected source across the complete returned ranking, assigning zero when absent; MRR@3 also assigns zero when absent from the top three. Abstention accuracy is reported separately for the four negative queries. The small, team-authored set is not an independent quality assessment.

After both scoped indexes are rebuilt against the frozen corpus, run from `apps/api`:

```sh
.venv/bin/python -B scripts/benchmark_policy_retrieval.py --output ../../docs/evidence/ai-for-good-retrieval-benchmark.json
```

The benchmark requires the same three vector environment variables and fails rather than describe a lexical fallback as hybrid. It records per-query top-three IDs, aggregate metrics, corpus and label hashes, and the current source commit. Comparing the two modes on these authored labels is descriptive only; it does not establish a semantic improvement, causation, or any real-world learning effect.

On 2026-11-05 UTC, the frozen-corpus local run returned the following on 36 positive and four abstention queries. These labels were written by the team before rankings were inspected and were not expert-validated. The full per-query evidence, input and executed-code hashes, and exact timestamp are in [the benchmark record](evidence/ai-for-good-retrieval-benchmark.json). The code was uncommitted at execution, so the recorded file hashes identify it precisely.

| Mode | Recall@3 | MRR | MRR@3 | Correct abstentions |
| --- | ---: | ---: | ---: | ---: |
| Lexical | 0.9722 | 0.9514 | 0.9444 | 3/4 |
| Hybrid | 1.0000 | 0.9444 | 0.9444 | 3/4 |

Both modes returned results for one unrelated football query. These scores describe this small authored set and do not establish general retrieval quality or practical outcomes.
