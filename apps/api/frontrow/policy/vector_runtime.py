"""Opt-in local vector subprocess; failures leave lexical retrieval available."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess


def vector_rankings(queries: list[str], institution: str) -> list[list[str]] | None:
    python = os.environ.get('FRONTROW_POLICY_VECTOR_PYTHON')
    model_dir = os.environ.get('FRONTROW_POLICY_VECTOR_MODEL')
    index_root = os.environ.get('FRONTROW_POLICY_VECTOR_INDEX_ROOT')
    if not all((python, model_dir, index_root)):
        return None
    script = Path(__file__).resolve().parents[2] / 'scripts' / 'policy_vector_worker.py'
    payload = {'queries': queries, 'institution': institution, 'model_dir': model_dir, 'index_root': index_root}
    try:
        process = subprocess.run([python, str(script)], input=json.dumps(payload), text=True,
                                 capture_output=True, timeout=45, check=True,
                                 env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
        rankings = json.loads(process.stdout)['rankings']
        if (not isinstance(rankings, list) or len(rankings) != len(queries)
                or any(not isinstance(row, list) or not row or any(not isinstance(x, str) for x in row) for row in rankings)):
            return None
        return rankings
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        return None
