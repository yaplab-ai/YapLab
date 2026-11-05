#!/usr/bin/env python3
"""Search the local notebook chunks with lexical TF-IDF; no model or network."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from frontrow.policy.chunk_index import ChunkIndex


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('query', help='words to search in the curated summaries')
    parser.add_argument('--institution', choices=('general', 'uaeu'), default='general')
    parser.add_argument('--limit', type=int, default=5)
    parser.add_argument('--bundle', type=Path, help='prepared bundle directory (default: scoped repository bundle)')
    args = parser.parse_args()
    bundle = args.bundle or (Path(__file__).resolve().parents[3] / 'knowledge-base' /
                             'itu-reference' / args.institution)
    try:
        index = ChunkIndex(bundle, institution=args.institution)
        results = index.search(args.query, args.limit)
    except (OSError, ValueError, RuntimeError) as exc:
        print(f'Policy chunk search failed: {exc}', file=sys.stderr)
        return 1
    print(json.dumps({
        'retrieval': 'local_lexical_tfidf_cosine',
        'institution': args.institution,
        'scope_warning': index.manifest['scope_warning'],
        'corpus_limitations': index.manifest['corpus_limitations'],
        'excerpt_notice': 'Each chunk is an excerpt of a curated summary and may omit or cut off relevant context and caveats; consult the complete summary and original source.',
        'limitations': 'Curated summaries, not full texts; lexical matches can miss relevant context. No neural embedding, FAISS index, or hosted import is implied.',
        'query': args.query,
        'results': results,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
