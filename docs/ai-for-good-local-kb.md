# Local policy knowledge base — 5 November 2026

The scoped notebook inputs remain in `knowledge-base/itu-reference/general` and
`knowledge-base/itu-reference/uaeu`. They contain original source summaries,
metadata and notebook-style chunks, not complete laws or university policies.
General has 10 documents / 29 chunks; UAEU adds three institutional examples for
13 documents / 38 chunks. Both bundles still pass the exporter’s exact check.

From `apps/api`, inspect actual prepared chunks without a model or network:

```bash
.venv/bin/python -B scripts/search_policy_chunks.py 'WCAG digital accessibility'
.venv/bin/python -B scripts/search_policy_chunks.py 'UAEU student academic credit generative AI' --institution uaeu
.venv/bin/python -B scripts/search_policy_chunks.py 'transfer conditions' --limit 2
.venv/bin/python -B verify_policy_chunk_index.py
```

The tool validates the scoped bundle against the corpus, then builds an
in-memory lexical TF-IDF index and ranks chunks by cosine similarity. It returns
exact chunk text/ID, source URL, institutional scope, document type, jurisdiction,
publication/retrieval dates and the source verification note. Scores rank text
matches; they are not legal relevance or confidence scores. Unmatched vocabulary
returns no results.

Chunks can cut off a sentence or caveat. Each result retains source metadata,
and the CLI also displays corpus limitations. In particular, a PDPL fragment
about transfers does not remove the recorded limitation that current statutory
text, transfer conditions and institutional applicability are unverified.
Read the complete summary and the primary source before interpreting a result.

This inspection CLI is separate from Policy Lab’s existing weighted lexical
source search and review. It does not change application routing, enable a
provider, create credentials, install dependencies or assert hosted ingestion.
It is useful for checking what the prepared input actually contains before
another system imports it.

## Built MiniLM / FAISS indexes

Separate real local vector indexes now exist at
[`knowledge-base/local-vector/general`](../knowledge-base/local-vector/general/)
and [`knowledge-base/local-vector/uaeu`](../knowledge-base/local-vector/uaeu/).
The general index contains **29 vectors**, and UAEU **38**, each with **384
normalized float32 dimensions** in FAISS `IndexFlatIP`. This follows the pinned
reference notebook's cell-9 embedding/index approach, using JSON metadata instead
of pickle. The notebook was not run in Google Drive; no ITU-hosted import occurred.

The model is `sentence-transformers/all-MiniLM-L6-v2`, pinned at revision
`1110a243fdf4706b3f48f1d95db1a4f5529b4d41`. Each index's `config.json` records the
model's Apache-2.0 source/license link, all ten model-file hashes, input/index/
metadata hashes, corpus version, scope and build library versions. Metadata
retains the exact chunk and its source URL, scope and verification note. The
input manifests under `itu-reference` remain unchanged: their
`embedding_index_built=false` describes those input packages. The separate vector
configs record `status=local_vector_index_built` and
`hosted_import_verified=false`.

The optional tooling runs separately from the application. No UI or app search
routing changed; Policy Lab still uses its existing weighted lexical source
search. Neither these small semantic probes nor similarity scores establish
retrieval quality, policy correctness or legal applicability.

### Use the existing temporary environment

From `apps/api` on this Mac:

```bash
/tmp/yaplab-vector-venv/bin/python -B scripts/vector_policy_kb.py search \
  --institution uaeu --model-dir /tmp/yaplab-vector-model \
  --index-dir ../../knowledge-base/local-vector/uaeu \
  --query 'student academic credit generative AI'
/tmp/yaplab-vector-venv/bin/python -B verify_policy_vector.py
```

Three real local-vector tests passed, including institution separation, the
UAEU student-policy probe, retained verification notes and changed-input/model/
index rejection. Three additional smoke queries returned TDRA accessibility,
UAEU student GenAI and PDPL transfer-summary chunks respectively. These are
hand-selected probes, not an accuracy benchmark. A first native ARM thread-pool
crash was resolved by limiting this standalone process to one native thread.

The environment and weights are temporary, outside the shared app dependencies:
`/tmp/yaplab-vector-venv` and `/tmp/yaplab-vector-model`. They may disappear on
cleanup. No model weights or dependency environments are committed.

### Reproduce setup and build

The hash-pinned wheel file targets **macOS ARM64 / Python 3.12**. Other platforms
need their own compatible dependency resolution. From `apps/api`, choose a fresh
optional environment; do not install into the shared application `.venv`:

```bash
.venv/bin/python -m venv /tmp/yaplab-vector-repro-venv
/tmp/yaplab-vector-repro-venv/bin/python -m pip --isolated install \
  --require-hashes --only-binary=:all: --no-cache-dir \
  --index-url https://pypi.org/simple \
  -r scripts/vector-requirements-macos-arm64-py312.txt
```

Setup downloads public packages/model files anonymously. It does not send corpus
content or create an account/token. For the public model, this snippet reads the
committed provenance and checks each file after download:

```bash
HF_HOME=/tmp/yaplab-vector-repro-cache HF_HUB_DISABLE_IMPLICIT_TOKEN=1 \
HF_HUB_DISABLE_TELEMETRY=1 /tmp/yaplab-vector-repro-venv/bin/python - <<'PYMODEL'
import hashlib, json
from pathlib import Path
from huggingface_hub import hf_hub_download
config = json.loads(Path('../../knowledge-base/local-vector/general/config.json').read_text())
for name, expected in config['model_file_sha256'].items():
    path = Path(hf_hub_download(config['embedding_model'], filename=name,
        revision=config['model_revision'], local_dir='/tmp/yaplab-vector-repro-model', token=False))
    assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, name
PYMODEL
```

Build and query then force local/offline loading; model and chunk data stay on
this machine. Use a fresh output directory:

```bash
/tmp/yaplab-vector-repro-venv/bin/python -B scripts/vector_policy_kb.py build \
  --institution general --model-dir /tmp/yaplab-vector-repro-model \
  --output /tmp/yaplab-vector-repro-general
```

Repeat with `--institution uaeu` and another fresh output directory if required.
The script checks the prepared input bundle against the current corpus before
building/searching. Hash checks detect drift relative to recorded provenance;
they do not authenticate arbitrarily supplied index files. Only load local
trusted outputs. The [submission workflow](ai-for-good-submission-workflow.md)
records the remaining hosted-format/access questions.

## Source scope and proposal review

The source checks retain the TDRA entity/service boundary, non-binding AI ethics
guidance, England’s comparative school/college scope and UAEU’s student/staff
boundary. Current statutory privacy text remains unverified. A source can be
eligible for retrieval yet weak for a particular incident action.

For each proposal, check role/stage-visible facts, whether the citation directly
supports the action or supplies context only, actual institutional applicability,
and human ownership/dependencies. Keep abstentions, partial results and negative
cases visible. Schema/ID acceptance is not semantic or legal validation. The
[existing source-fit review](ai-for-good-source-review-and-next-steps.md) records
concrete weak historical matches; no new live proposal was produced by this work.

## Current paid evaluation status

On 5 November the current protocol-3 / corpus-.4 plan matched all 27 saved prompt
hashes and passed 43 focused preflight tests. The proposed run was one Nebius
Nano evaluation, at most 27 attempts × 400 output tokens, no retries or fallback,
using only synthetic facts and public-policy notes with the existing key.

Automatic approval review **denied process creation before execution**, citing
that prior bounded-test approval did not authorise another paid run and that
the latest instructions prohibited additional paid calls. No SDK/provider
attempt began and no new provider cost was incurred. A specific approval request
is pending; the denied operation has not been retried.
The current UI verification used fake/scripted providers only.

The public [Nebius model page](https://nebius.com/services/token-factory/models/nvidia-nemotron-models-inference)
was read in the browser on 5 November and showed Nano rates of $0.06/M input and
$0.24/M output. The planning estimate is $0.02761824, not an enforced billing cap
or account/invoice verification. Do not treat the blocked run as live evidence.

## Verification record

This increment passed 90 existing backend checks, 100 policy/evidence tests
(including four new lexical checks), three separate optional vector tests,
standalone scenario and both bundle checks, 98 frontend tests, frontend build
and an offline API package build. A fresh fake/scripted browser walkthrough
verified classroom → report → staged policy review → decision/audit. Existing
frontend bundle-size warnings remain. See the [machine-readable record](evidence/ai-for-good-kb-2026-11-05.json).
