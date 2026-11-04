# YapLab policy knowledge base inputs

These are local source-summary packages for the notebook linked from the ITU
event, not a hosted or distributed index. They contain links, provenance,
original paraphrases and applicability cautions, without mirrored source PDFs.

| Collection | Source records | Use |
| --- | --- | --- |
| `itu-reference/general` | 8 | General references; institutional examples excluded |
| `itu-reference/uaeu` | 11 | General references plus 3 UAEU-only examples, explicitly selected |

Each collection has a flat `docs` folder, `manifest.json` and `chunks.jsonl`.
Only the chosen collection's `docs` files belong in the notebook's ingestion
folder. Manifests and chunks stay outside it. The manifest maps notebook source
filenames to source IDs, URLs, file SHA-256 hashes, scope and reuse notes. Do not
mix the two collections or assume the reference notebook enforces YapLab's
institution filter.

The exporter pins upstream commit `84010da9e9c443afcceeccb86d1700a662223395` and
retains its MIT notice for the adapted normalizer/chunker. Source publications
retain their own rights. UAEU restricts reproduction of its material, so this
package supplies concise original notes and links. Rights review is required
before expanding to full-text mirroring.

Run `verify_policy_export.py` and the scoped `--check` commands in the
[workflow findings](../docs/ai-for-good-submission-workflow.md#local-package-and-reproduction)
to verify deterministic files and detect drift. No provider calls, embeddings,
Google Drive authentication, external uploads or accepted ITU-hosted imports
were part of package preparation. The exact final submission/import channel
still needs organiser confirmation.
