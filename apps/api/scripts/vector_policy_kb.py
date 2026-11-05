#!/usr/bin/env python3
"""Build or search local MiniLM/FAISS indexes; no network or pickle.

The pinned ITU notebook Cell 9 uses normalized all-MiniLM-L6-v2 vectors and
FAISS IndexFlatIP. This separate local implementation uses JSON metadata.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

# Keep model loading and inference offline, and avoid implicit HF credentials.
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
os.environ['HF_HUB_DISABLE_IMPLICIT_TOKEN'] = '1'
os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
os.environ['TOKENIZERS_PARALLELISM'] = 'false'
os.environ['HF_HOME'] = '/tmp/yaplab-vector-cache'
# Bound native thread pools on CPU; this also avoids an observed ARM64 crash.
for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[name] = '1'

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import sentence_transformers
import torch
import transformers

ROOT = Path(__file__).resolve().parents[3]
API = ROOT / 'apps' / 'api'
REVISION = '1110a243fdf4706b3f48f1d95db1a4f5529b4d41'
MODEL = 'sentence-transformers/all-MiniLM-L6-v2'
MODEL_HASHES = {
    '1_Pooling/config.json': '4be450dde3b0273bb9787637cfbd28fe04a7ba6ab9d36ac48e92b11e350ffc23',
    'config.json': '953f9c0d463486b10a6871cc2fd59f223b2c70184f49815e7efbcab5d8908b41',
    'config_sentence_transformers.json': '061ca9d39661d6c6d6de5ba27f79a1cd5770ea247f8d46412a68a498dc5ac9f3',
    'model.safetensors': '53aa51172d142c89d9012cce15ae4d6cc0ca6895895114379cacb4fab128d9db',
    'modules.json': '84e40c8e006c9b1d6c122e02cba9b02458120b5fb0c87b746c41e0207cf642cf',
    'sentence_bert_config.json': 'fc1993fde0a95c24ec6c022539d41cf6e2f7c9721e5415d6fb6897472a9cd4b7',
    'special_tokens_map.json': '303df45a03609e4ead04bc3dc1536d0ab19b5358db685b6f3da123d05ec200e3',
    'tokenizer.json': 'be50c3628f2bf5bb5e3a7f17b1f74611b2561a3a27eeab05e5aa30f411572037',
    'tokenizer_config.json': 'acb92769e8195aabd29b7b2137a9e6d6e25c476a4f15aa4355c233426c61576b',
    'vocab.txt': '07eced375cec144d27c900241f3e339478dec958f92fddbc551f295c992038a3',
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def versions() -> dict:
    return {'python': sys.version.split()[0], 'sentence_transformers': sentence_transformers.__version__,
            'transformers': transformers.__version__, 'torch': torch.__version__,
            'faiss': faiss.__version__, 'numpy': np.__version__}


def model_load(path: Path):
    for name, expected in MODEL_HASHES.items():
        if digest(path / name) != expected:
            raise ValueError(f'model file differs from pinned revision: {name}')
    # Explicit path plus local_files_only precludes network-based model resolution.
    return SentenceTransformer(str(path), device='cpu', local_files_only=True)


def bundle_data(institution: str):
    path = ROOT / 'knowledge-base' / 'itu-reference' / institution
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    check = subprocess.run([str(API / '.venv/bin/python'), str(API / 'scripts/export_policy_kb.py'),
                            '--check', '--institution', institution, '--output', str(path)],
                           capture_output=True, text=True, env=env)
    if check.returncode:
        raise ValueError('prepared bundle failed exact corpus validation: ' + check.stderr.strip())
    manifest = json.loads((path / 'manifest.json').read_text(encoding='utf-8'))
    chunks = [json.loads(line) for line in (path / 'chunks.jsonl').read_text(encoding='utf-8').splitlines()]
    files = [path / 'manifest.json', path / 'chunks.jsonl', *sorted((path / 'docs').glob('*.md'))]
    hashes = {str(p.relative_to(path)): digest(p) for p in files}
    return manifest, chunks, hashes


def metadata_records(manifest: dict, chunks: list[dict]) -> list[dict]:
    records = []
    for chunk in chunks:
        source = manifest['sources'][chunk['source']]
        records.append({**chunk, 'source_id': source['id'], 'source_url': source['url'],
                        'source_scope': source['scope'], 'source_verification': source['verification'],
                        'source_institution': source['institution'],
                        'source_document_type': source['document_type'],
                        'source_jurisdiction': source['jurisdiction'],
                        'source_published': source['published'], 'source_retrieved': source['retrieved']})
    return records


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def build(args) -> None:
    manifest, chunks, hashes = bundle_data(args.institution)
    model = model_load(args.model_dir)
    embeddings = model.encode([c['text'] for c in chunks], convert_to_numpy=True,
                              normalize_embeddings=True, show_progress_bar=False)
    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings.astype('float32'))
    # Require a fresh location so existing results cannot be overwritten.
    args.output.mkdir(parents=True, exist_ok=False)
    faiss.write_index(index, str(args.output / 'faiss.index'))
    write_json(args.output / 'metadata.json', metadata_records(manifest, chunks))
    config = {
        'status': 'local_vector_index_built', 'hosted_import_verified': False,
        'institution': args.institution, 'corpus_version': manifest['corpus_version'],
        'notebook_reference': manifest['notebook_reference']['repository'],
        'notebook_commit': manifest['notebook_reference']['commit'], 'notebook_cell': 'Cell 9',
        'embedding_model': MODEL, 'model_revision': REVISION, 'model_license': 'Apache-2.0',
        'model_license_reference': f'https://huggingface.co/{MODEL}/blob/{REVISION}/README.md',
        'model_file_sha256': MODEL_HASHES, 'library_versions': versions(),
        'encoding': {'normalized': True, 'dtype': 'float32', 'device': 'cpu'},
        'index_type': 'IndexFlatIP', 'dimension': index.d, 'vectors': index.ntotal,
        'bundle_sha256': hashes, 'metadata_sha256': digest(args.output / 'metadata.json'),
        'index_sha256': digest(args.output / 'faiss.index'),
        'scope_warning': manifest['scope_warning'], 'corpus_limitations': manifest['corpus_limitations'],
    }
    write_json(args.output / 'config.json', config)
    print(f'Built local {args.institution} index: {index.ntotal} vectors, {index.d} dimensions')


def search(args) -> None:
    if not args.query.strip() or not 1 <= args.limit <= 100:
        raise ValueError('query must be nonempty and limit must be between 1 and 100')
    manifest, chunks, hashes = bundle_data(args.institution)
    config = json.loads((args.index_dir / 'config.json').read_text(encoding='utf-8'))
    if (config['institution'] != args.institution or config['bundle_sha256'] != hashes
            or config['corpus_version'] != manifest['corpus_version']):
        raise ValueError('index scope or input hashes differ from current bundle')
    if (config['embedding_model'] != MODEL or config['model_revision'] != REVISION
            or config['model_file_sha256'] != MODEL_HASHES):
        raise ValueError('model differs from index provenance')
    if (digest(args.index_dir / 'metadata.json') != config['metadata_sha256']
            or digest(args.index_dir / 'faiss.index') != config['index_sha256']):
        raise ValueError('index or metadata file hash differs from provenance')
    records = json.loads((args.index_dir / 'metadata.json').read_text(encoding='utf-8'))
    if records != metadata_records(manifest, chunks):
        raise ValueError('metadata differs from validated bundle chunks')
    # Load only a locally produced, hash-checked FAISS index; never untrusted files.
    index = faiss.read_index(str(args.index_dir / 'faiss.index'))
    if (not isinstance(index, faiss.IndexFlatIP) or index.d != config['dimension']
            or index.ntotal != len(records) or index.ntotal != config['vectors']):
        raise ValueError('FAISS index shape or type differs from provenance')
    model = model_load(args.model_dir)
    vector = model.encode([args.query], convert_to_numpy=True, normalize_embeddings=True,
                          show_progress_bar=False).astype('float32')
    scores, ids = index.search(vector, min(args.limit, len(records)))
    results = []
    for score, pos in zip(scores[0], ids[0]):
        chunk = records[int(pos)]
        source = manifest['sources'][chunk['source']]
        results.append({'source_id': source['id'], 'source_url': source['url'],
                        'source_scope': source['scope'], 'source_institution': source['institution'],
                        'source_verification': source['verification'],
                        'source_document_type': source['document_type'],
                        'source_jurisdiction': source['jurisdiction'], 'source_published': source['published'],
                        'source_retrieved': source['retrieved'], 'source_file': chunk['source'],
                        'chunk_id': chunk['chunk_id'], 'text': chunk['text'], 'score': float(score)})
    print(json.dumps({'retrieval': 'local_minilm_normalized_faiss_inner_product',
                      'institution': args.institution, 'query': args.query,
                      'scope_warning': manifest['scope_warning'], 'corpus_limitations': manifest['corpus_limitations'],
                      'excerpt_notice': 'Each chunk is an excerpt of a curated summary and may omit or cut off relevant context and caveats; consult the complete summary and original source.',
                      'limitations': 'Similarity scores are not confidence or applicability; semantic retrieval can miss relevant context. No hosted import is implied.',
                      'results': results}, ensure_ascii=False, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('build', 'search'))
    parser.add_argument('--institution', choices=('general', 'uaeu'), default='general')
    parser.add_argument('--model-dir', type=Path, required=True, help='verified local model files; no download')
    parser.add_argument('--output', type=Path, help='new directory for build')
    parser.add_argument('--index-dir', type=Path, help='local index directory for search')
    parser.add_argument('--query', default='', help='search query')
    parser.add_argument('--limit', type=int, default=4)
    args = parser.parse_args()
    if args.action == 'build' and args.output is None:
        parser.error('build requires --output')
    if args.action == 'search' and args.index_dir is None:
        parser.error('search requires --index-dir')
    try:
        build(args) if args.action == 'build' else search(args)
    except (OSError, ValueError, RuntimeError, KeyError, TypeError) as exc:
        print(f'Local vector KB failed: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
