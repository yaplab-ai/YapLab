# Local policy knowledge base — 5 November 2026

The scoped notebook inputs remain in `knowledge-base/itu-reference/general` and
`knowledge-base/itu-reference/uaeu`. They contain original source summaries,
metadata, display summaries and verified text assets, with notebook-style chunks.
Frozen corpus `2026-11-05.5` has 25 records. General has 22 documents / 126 chunks;
UAEU adds three institutional examples for 25 documents / 135 chunks. Both bundles
pass the exporter’s exact check. Thirteen assets supply original text: three
contain relevant sections (UAE AI ethics, FERPA and DOJ web guidance), while ten
contain short attributed locator excerpts. This is not a full national corpus.

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
The general index contains **126 vectors**, and UAEU **135**, each with **384
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

The optional isolated vector worker now supplies app hybrid retrieval when
configured; lexical mode remains the default fallback. The inspection CLI is
separate. Neither similarity scores nor small probes establish policy correctness
or legal applicability. The pre-labelled benchmark below is limited team evidence.

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


## National-document coverage and rights

| Brief category | Status | Included material and precise limit |
| --- | --- | --- |
| Law | Partial | UAE PDPL/disability source notes and indexed locators; full current statutory text/amendments not verified. Selected FERPA text is a foreign comparison, not national coverage. |
| AI, digital and cyber strategies | Partial | AI strategy/charter, digital-government strategy to 2025, 2019 cybersecurity reference and licensed ethics sections. Strategy periods/current replacement require care; guidance is not a university mandate. |
| Data protection | Partial | Scoped PDPL notes, ethics privacy sections, UAEU governance example and FERPA comparison; cross-border/application questions remain unresolved. |
| Institutional mandates | Partial | CAA public higher-education evaluation overview and UAEU-only examples. Detailed former 2019 standards and actual university incident/assessment/support procedures are unverified. |
| IP regime | Missing verified national text | Official copyright-law endpoints were inaccessible. No lecture-recording permission or statutory exception is inferred. |
| Multilateral commitments | Partial | UNESCO recommendations/guidance and OECD principles provide comparison. They do not prove UAE treaty ratification or adoption of every instrument. |
| Energy/infrastructure | Partial | Digital/cyber strategy context and local inference setup; no dedicated national energy-policy text, energy measurement or infrastructure readiness score. |

Each text asset has a source URL, locator, retrieval date, content hash and rights
basis. UAE ethics sections are CC BY 4.0; the selected U.S. government material
is public-domain source text. Unclear publisher rights lead to locator excerpts,
not inferred permission to mirror whole PDFs. Source rights and separate TalkMoves
restrictions remain distinct from the MIT code licence. The app's source cards
continue to display original paraphrases and cautions.

The optional hybrid path now supplies the application's source search, not just
an inspection CLI; its result explicitly reports `hybrid` or `lexical`. It uses
existing institutional filters and a lexical overlap gate. Missing dependencies,
invalid local artifacts or absent opt-in configuration fall back to lexical.
[Setup, benchmark and limitations](ai-for-good-retrieval.md) include the frozen
40-query labels: recall@3 0.9722 lexical / 1.0000 hybrid, MRR 0.9514 / 0.9444;
both correctly abstained on three of four unrelated queries. These team-authored
labels are not expert validation or an educational benchmark. The optional
worker requires the repository scripts and external model/index setup; a wheel
without those files retains lexical fallback.

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

## Earlier protocol-3 evaluation status

On 5 November the current protocol-3 / corpus-.4 plan matched all 27 saved prompt
hashes and passed 43 focused preflight tests. The proposed run was one Nebius
Nano evaluation, at most 27 attempts × 400 output tokens, no retries or fallback,
using only synthetic facts and public-policy notes with the existing key.

Automatic approval review initially **denied process creation before execution**,
with zero provider requests. The user then explicitly approved the corrected
roughly $0.028 bounded estimate. One retry was permitted and completed all 27
requests: **25 fully accepted roles, two partial, zero unavailable**. Reported
usage gives **$0.00354984** at the checked list prices; invoice/account charge is
unverified. No additional run, retry or fallback occurred. See the
[actual results and source-fit review](ai-for-good-v3-results.md).

The public [Nebius model page](https://nebius.com/services/token-factory/models/nvidia-nemotron-models-inference)
was checked on 5 November: $0.06/M input, $0.24/M output. The $0.02761824 planning
estimate was not an enforced dollar cap. The earlier [KB verification record](evidence/ai-for-good-kb-2026-11-05.json)
records the initial blocked state; the separate live artifact records its later
resolution. The local UI walkthrough in that earlier record remains fake/scripted.

## Verification record

This increment passed 90 existing backend checks, 100 policy/evidence tests
(including four new lexical checks), three separate optional vector tests,
standalone scenario and both bundle checks, 98 frontend tests, frontend build
and an offline API package build. A fresh fake/scripted browser walkthrough
verified classroom → report → staged policy review → decision/audit. Existing
frontend bundle-size warnings remain. See the [machine-readable record](evidence/ai-for-good-kb-2026-11-05.json).

## Final-push protocol4 status

The current implementation uses corpus `2026-11-05.5` and protocol4. The new
app-level paid run was denied before process creation: zero calls/new cost,
fresh approval pending. [Current status and commands](ai-for-good-v4-results.md)
supersede the earlier protocol3 status above. The historical results and source
artifacts were not rewritten.
