# AI for Good submission and knowledge base workflow

Public instructions/reference code checked on 4 November 2026; local-vector
status updated on 5 November. No new deliverable has been uploaded or submitted.

## Confirmed submission requirements

The [official event page](https://aiforgood.itu.int/event/ai-for-good-sandbox-hackathon-united-arab-emirates/?topic=485)
lists 10 November 2026 as the deadline, a report of at most five pages, a GitHub
repository and a policy knowledge base. The initial video is optional, at most
seven minutes; shortlisted teams need it. It asks for progressive incidents,
auditability, standards mapping and domain-specific gaps with global examples.

The [public application form](https://aiforgood.itu.int/ai-for-good-sandbox-hackathon-uae-apply/)
is for registration. The FAQ says detailed team information will later be recorded
in Google Sheets, without supplying that sheet or identifying it as a deliverable
upload. Sandbox access is described for selected participants. The available
registration acknowledgment does not confirm sandbox selection or provide an
import destination. No private email contents or account details are included here.

**Unconfirmed:** final submission URL, cutoff time and timezone, team-edit sheet,
hosted KB endpoint, authentication, accepted hosted schema and acceptance of
source-linked summaries rather than full-text source documents. Absence from the
reviewed material does not establish that no private instructions exist.

## What the linked reference code actually does

The event links [ITUAIReadiness](https://github.com/CrashingGuru/ITUAIReadiness).
We inspected commit **84010da9e9c443afcceeccb86d1700a662223395** from a read-only
local clone. The code is MIT-licensed; its notice accompanies the adapted chunker.

The [pinned Colab notebook](https://github.com/CrashingGuru/ITUAIReadiness/blob/84010da9e9c443afcceeccb86d1700a662223395/Colab%20Free%20Tier%20LLM%20Notebook.ipynb)
implements a local personal-Drive workflow:

| Logical cell | Local operation | Important boundary |
| --- | --- | --- |
| 4 and 5 | Configure project folders and mount personal Google Drive | Requires the user's Drive authorization; this was not performed |
| 7 | Accept PDF, TXT and MD uploads into `docs` | Input types, not a confirmed final-submission specification |
| 8 | Read the immediate `docs` folder, normalize and chunk text | Flat folder; 800-character chunks, 120-character overlap, minimum 80 |
| 9 | Embed with all-MiniLM-L6-v2 and save FAISS plus metadata/config | Not run in Drive; equivalent local MiniLM/FAISS preparation now exists separately |

Cell 8 emits `{source: filename, chunk_id: integer, text: string}` records. Cell 9
writes `faiss.index`, `metadata.pkl` and `config.json`. These are that notebook's
local persistence files. The public code does not establish them as an ITU-hosted
import format or provide hosted access credentials. Its pickled metadata is not
needed for YapLab's safe JSON export.

The repository also has a distinct [local simulation ingestion path](https://github.com/CrashingGuru/ITUAIReadiness/blob/84010da9e9c443afcceeccb86d1700a662223395/simulation/server/knowledge/ingest.py)
using Ollama and ChromaDB. Its file parser accepts Markdown, but it has a different
chunker and filename-based source/country inference. The country patterns do not
include UAE, and some YapLab filenames would receive an unsuitable source type.
Its `extra_metadata` parameter can override metadata programmatically, but no
hosted adapter or accepted external schema has been verified. Do not treat a
notebook-compatible folder as validated Chroma or hosted ingestion.

## Local package and reproduction

`knowledge-base/itu-reference` contains separate **general** and **uaeu**
collections. Each has a flat `docs` directory plus `manifest.json` and
`chunks.jsonl` outside the ingestion directory. Import only the chosen collection's
`docs` files into the notebook. The manifests identify the selected context,
source IDs and URLs, file hashes, rights and verification notes, and the pinned
chunking reference. Institutional scope still needs to be enforced by any external
consumer; the reference notebook does not supply YapLab's API scope filter.

The content is curated metadata and original summaries, not mirrored legislation
or university PDFs. The local package is not a distributed vector store. Its
manifest explicitly marks hosted import and embedding-index creation as false
for these input packages. Separate [`local-vector`](../knowledge-base/local-vector/)
outputs now contain real local MiniLM/FAISS indexes: 29 general / 38 UAEU vectors,
384 normalized dimensions, JSON metadata and pinned model/input provenance.
Their configs mark local construction and `hosted_import_verified=false`.
This is an independent local adaptation of cell 9, not execution of the Drive
notebook or a validated ITU-hosted schema. [Setup and tests](ai-for-good-local-kb.md)
use a separate temporary environment; Policy Lab's application search is unchanged.

From `apps/api` in the isolated worktree:

```bash
.venv/bin/python verify_policy_export.py
.venv/bin/python scripts/export_policy_kb.py --institution general --output ../../knowledge-base/itu-reference/general --check
.venv/bin/python scripts/export_policy_kb.py --institution uaeu --output ../../knowledge-base/itu-reference/uaeu --check
```

To regenerate, choose a fresh empty output directory and omit `--check`. The
exporter refuses to overwrite a nonempty directory or follow output symlinks.
It performs no network, model download, authentication, upload or provider call.

## Questions requiring organiser confirmation

1. What is the final submission destination and deadline time/timezone, and where
   should team details be completed?
2. Is a source-linked summary corpus accepted, or is rights-cleared full text
   required? What KB files, metadata and import schema should be supplied?
3. Is hosted ingestion required before the deadline? If so, what official
   endpoint, access procedure and participant eligibility apply?
4. Are the notebook and simulation alternative examples, and which one should be
   used to demonstrate compatibility?
5. Does structured audit evidence with concise decision summaries and citations
   meet the audit requirement without private model chain-of-thought?

These questions are prepared for review; no message has been sent. The code and
local package can be completed while awaiting answers, but hosted acceptance
cannot be claimed without them.

## Report template inspection and remaining authoring gate

The [downloaded official template](https://s41721.pcdn.co/wp-content/uploads/2022/06/AI-for-Good-Sandbox-Hackathon-submission-template.docx)
was inspected read-only. It uses one US Letter section with one-inch margins,
team/contact/repository fields and a pipeline mapping table. Its sample smart-pen
and school text is illustrative and must be replaced with YapLab's actual scope.
The report content draft maps to its use case, requirements, architecture/readiness,
scenario and gap sections. Final team details and a reviewed repository destination
remain to be supplied.

DOCX rendering/pagination is **not verified** on this host. The Documents skill
requires the bundled workspace runtime; the dependency loader reports that it
supports local threads only and did not supply a runtime here. No alternative
system installation was substituted, and no unrendered DOCX is presented as a
finished five-page report. The Markdown content draft remains reviewable.
