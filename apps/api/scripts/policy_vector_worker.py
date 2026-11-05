#!/usr/bin/env python3
"""Offline, batch-only vector worker; invoked by the API's configured interpreter."""
from __future__ import annotations

import json
from pathlib import Path
import sys

import vector_policy_kb as v


def main():
    payload = json.load(sys.stdin)
    institution = payload['institution']
    if institution not in ('general', 'uaeu'):
        raise ValueError('invalid scope')
    queries = payload['queries']
    if not isinstance(queries, list) or not queries or len(queries) > 100 or any(not isinstance(q, str) or len(q) > 8000 for q in queries):
        raise ValueError('invalid queries')
    index_dir = Path(payload['index_root']) / institution
    manifest, chunks, hashes = v.bundle_data(institution)
    config = json.loads((index_dir / 'config.json').read_text(encoding='utf-8'))
    if (config['institution'] != institution or config['bundle_sha256'] != hashes
            or config['corpus_version'] != manifest['corpus_version']):
        raise ValueError('index scope or bundle differs')
    if (config['embedding_model'] != v.MODEL or config['model_revision'] != v.REVISION
            or config['model_file_sha256'] != v.MODEL_HASHES):
        raise ValueError('model provenance differs')
    if (v.digest(index_dir / 'metadata.json') != config['metadata_sha256']
            or v.digest(index_dir / 'faiss.index') != config['index_sha256']):
        raise ValueError('index or metadata hash differs')
    records = json.loads((index_dir / 'metadata.json').read_text(encoding='utf-8'))
    if records != v.metadata_records(manifest, chunks):
        raise ValueError('metadata differs from bundle')
    index = v.faiss.read_index(str(index_dir / 'faiss.index'))
    if (not isinstance(index, v.faiss.IndexFlatIP) or index.d != config['dimension']
            or index.ntotal != len(records) or index.ntotal != config['vectors']):
        raise ValueError('index shape differs')
    model = v.model_load(Path(payload['model_dir']))
    vectors = model.encode(queries, convert_to_numpy=True, normalize_embeddings=True,
                           show_progress_bar=False).astype('float32')
    scores, ids = index.search(vectors, len(records))
    rankings = []
    for positions in ids:
        seen = set()
        source_ids = []
        for position in positions:
            source_id = records[int(position)]['source_id']
            if source_id not in seen:
                seen.add(source_id)
                source_ids.append(source_id)
        rankings.append(source_ids)
    print(json.dumps({'rankings': rankings}))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError, KeyError, TypeError) as exc:
        print(f'Local vector worker failed: {exc}', file=sys.stderr)
        raise SystemExit(1)
