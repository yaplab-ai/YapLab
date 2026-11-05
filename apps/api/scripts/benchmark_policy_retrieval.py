#!/usr/bin/env python3
"""Evaluate the frozen team labels, using the app's retrieval and local vector worker."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

API = Path(__file__).resolve().parents[1]
ROOT = API.parents[1]
sys.path.insert(0, str(API))
from frontrow.policy.evidence import fuse_rankings, lexical_search, load_corpus, scoped_sources
from frontrow.policy.vector_runtime import vector_rankings


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    labels_path = API / 'frontrow/policy/retrieval_labels.json'
    labels = json.loads(labels_path.read_text(encoding='utf-8'))
    corpus = load_corpus()
    source_ids = {s.id for s in corpus.entries}
    for row in labels['queries']:
        if not set(row['expected_source_ids']) <= source_ids:
            raise ValueError(f"unknown expected source ID in {row['id']}")
        allowed = {s.id for s in scoped_sources(corpus, row['institution'])}
        if not set(row['expected_source_ids']) <= allowed:
            raise ValueError(f"out-of-scope expected source ID in {row['id']}")
    ranked = {}
    for scope in ('general', 'uaeu'):
        selected = [row for row in labels['queries'] if row['institution'] == scope]
        vectors = vector_rankings([row['query'] for row in selected], scope)
        if vectors is None:
            raise RuntimeError(f'vector runtime unavailable or invalid for {scope}; refusing to label lexical results hybrid')
        ranked.update({row['id']: vector for row, vector in zip(selected, vectors)})
    results = []
    for row in labels['queries']:
        entries = scoped_sources(corpus, row['institution'])
        allowed = {s.id:s for s in entries}
        lex = lexical_search(corpus, row['query'], limit=len(entries), institution=row['institution'])
        hybrid = fuse_rankings(lex, ranked[row['id']], allowed, len(entries)) if lex else []
        expected = set(row['expected_source_ids'])
        lexical_ids = [h['id'] for h in lex]
        hybrid_ids = [h['id'] for h in hybrid]
        def first_rank(ids):
            return next((i for i, source_id in enumerate(ids, 1) if source_id in expected), None)
        results.append({'query_id':row['id'], 'scenario':row['scenario'],
                        'lexical_top3':lexical_ids[:3], 'hybrid_top3':hybrid_ids[:3],
                        'lexical_first_relevant_rank':first_rank(lexical_ids),
                        'hybrid_first_relevant_rank':first_rank(hybrid_ids),
                        'expected_source_ids':row['expected_source_ids'], 'should_abstain':row['should_abstain']})
    def metrics(mode):
        positive=[r for r in results if not r['should_abstain']]
        abstain=[r for r in results if r['should_abstain']]
        recall=[]; reciprocal=[]; reciprocal_full=[]
        for r in positive:
            expected=set(r['expected_source_ids']); found=r[mode+'_top3']
            recall.append(len(expected & set(found))/len(expected))
            reciprocal.append(next((1/i for i,x in enumerate(found,1) if x in expected),0))
            rank = r[mode+'_first_relevant_rank']
            reciprocal_full.append(1/rank if rank else 0)
        return {'relevant_queries':len(positive), 'recall_at_3':sum(recall)/len(recall),
                'mrr':sum(reciprocal_full)/len(reciprocal_full),
                'mrr_at_3':sum(reciprocal)/len(reciprocal), 'abstain_queries':len(abstain),
                'correct_abstentions':sum(not r[mode+'_top3'] for r in abstain),
                'abstention_accuracy':sum(not r[mode+'_top3'] for r in abstain)/len(abstain)}
    source_commit = subprocess.run(['git','rev-parse','HEAD'], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    code_paths = ['frontrow/policy/evidence.py', 'frontrow/policy/vector_runtime.py',
                  'scripts/policy_vector_worker.py', 'scripts/vector_policy_kb.py',
                  'scripts/benchmark_policy_retrieval.py']
    index_root = Path(os.environ['FRONTROW_POLICY_VECTOR_INDEX_ROOT'])
    code_hashes = {name: sha(API/name) for name in code_paths}
    code_status = subprocess.run(['git', 'status', '--porcelain', '--',
                                  *['apps/api/' + name for name in code_paths]],
                                 cwd=ROOT, capture_output=True, text=True, check=True).stdout
    index_hashes = {scope: {name: sha(index_root/scope/name)
                            for name in ('config.json', 'metadata.json', 'faiss.index')}
                    for scope in ('general', 'uaeu')}
    result={'status':'team-authored, not expert-validated', 'generated_at_utc':datetime.now(timezone.utc).isoformat(),
            'labels_sha256':sha(labels_path), 'label_freeze_utc':labels['frozen_at_utc'],
            'corpus_sha256':sha(API/'frontrow/policy/corpus.json'), 'corpus_version':corpus.version,
            'source_commit':source_commit, 'working_tree_note':('Retrieval files have uncommitted changes; component hashes identify the executed files.' if code_status else 'Retrieval files match the recorded commit.'),
            'retrieval_code_sha256':code_hashes, 'index_sha256':index_hashes,
            'metric_definition':labels['metric_definition'],
            'scope':'Local offline retrieval comparison; source relevance labels are incomplete, and scores do not establish legal applicability or educational outcomes.',
            'retrieval':'Lexical uses weighted source metadata; hybrid uses reciprocal rank fusion of lexical ranks and verified local MiniLM/FAISS chunk-derived source ranks, with a lexical overlap gate.',
            'lexical':metrics('lexical'), 'hybrid':metrics('hybrid'), 'queries':results}
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({key:result[key] for key in ('labels_sha256','corpus_sha256','lexical','hybrid')},indent=2))

if __name__ == '__main__':
    main()
