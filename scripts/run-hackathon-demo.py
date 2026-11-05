#!/usr/bin/env python3
"""Run the complete synthetic demo locally using installed dependencies only."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
VECTOR_KEYS = ('FRONTROW_POLICY_VECTOR_PYTHON', 'FRONTROW_POLICY_VECTOR_MODEL',
               'FRONTROW_POLICY_VECTOR_INDEX_ROOT')


def configure_vectors(env: dict[str, str], root: Path = ROOT, defaults: tuple[str, str, str] | None = None) -> str:
    """Use local defaults only when no vector setting was explicitly supplied."""
    if any(key in env for key in VECTOR_KEYS):
        return 'explicit settings'  # Incomplete or invalid settings fall back in the worker.
    defaults = defaults or ('/tmp/yaplab-vector-venv/bin/python', '/tmp/yaplab-vector-model',
                            str(root / 'knowledge-base/local-vector'))
    python, model, indexes = map(Path, defaults)
    if (python.is_file() and os.access(python, os.X_OK) and model.is_dir()
            and all((indexes / scope / name).is_file() for scope in ('general', 'uaeu')
                    for name in ('config.json', 'metadata.json', 'faiss.index'))):
        env.update(dict(zip(VECTOR_KEYS, defaults)))
        return 'automatic local defaults'
    return 'local vector files unavailable'


def retrieval_probe(api_url: str, institution: str) -> str:
    """Ask the local search endpoint which mode actually served a known query."""
    payload = json.dumps({'query': 'student data privacy', 'institution': institution, 'limit': 3}).encode()
    request = Request(api_url + '/policy/search', data=payload,
                      headers={'Content-Type': 'application/json'}, method='POST')
    try:
        with urlopen(request, timeout=50) as response:
            mode = json.load(response).get('retrieval_mode')
        return mode if mode in ('hybrid', 'lexical') else 'unknown'
    except (OSError, ValueError, TypeError, AttributeError):
        return 'unknown'


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--api-port', type=int, default=8765)
    parser.add_argument('--ui-port', type=int, default=5179)
    parser.add_argument('--replay-live', metavar='RECORDING.json', type=Path,
                        help='Open a saved live exercise read-only; pass its exported JSON file.')
    args = parser.parse_args()
    if args.replay_live and not args.replay_live.is_file():
        parser.error('The replay recording must be an existing JSON file.')
    if not (1 <= args.api_port <= 65535 and 1 <= args.ui_port <= 65535) or args.api_port == args.ui_port:
        parser.error('Use two distinct ports from 1 to 65535.')
    api_url = f'http://127.0.0.1:{args.api_port}'
    ui_url = f'http://127.0.0.1:{args.ui_port}'
    python = ROOT / 'apps/api/.venv/bin/python'
    node = shutil.which('node')
    if not python.exists() or not node or not (ROOT / 'frontend/node_modules/vite').is_dir():
        print('Installed API .venv, Node.js and frontend node_modules are required. See README quick start.', file=sys.stderr)
        return 1
    # Refuse occupied ports rather than accidentally displaying another app.
    for port in (args.api_port, args.ui_port):
        try:
            with socket.socket() as probe:
                probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                probe.bind(('127.0.0.1', port))
        except OSError:
            print(f'Port {port} is occupied. Stop the process using it, then retry.', file=sys.stderr)
            return 1
    env = os.environ.copy()
    env.update({
        'FRONTROW_LLM': 'fake', 'FRONTROW_POLICY_LLM': 'off',
        'FRONTROW_POLICY_COORDINATION': 'demo', 'FRONTROW_TTS': 'none', 'FRONTROW_STT': 'none',
        'FRONTROW_TICK_INTERVAL_SECONDS': '3', 'FRONTROW_MODERATOR_WARMUP_SECONDS': '0',
        'FRONTROW_MODERATOR_WARMUP_MIN_WORDS': '0', 'FRONTROW_CORS_ORIGINS': ui_url,
        'VITE_API_URL': api_url, 'VITE_HACKATHON_DEMO': '1', 'PYTHONUNBUFFERED': '1',
        'VITE_POLICY_REPLAY': '1' if args.replay_live else '0',
    })
    vector_config = configure_vectors(env)
    if args.replay_live:
        env['FRONTROW_POLICY_REPLAY_PATH'] = str(args.replay_live.resolve())
    else:
        env.pop('FRONTROW_POLICY_REPLAY_PATH', None)
    processes: list[subprocess.Popen] = []
    try:
        processes.append(subprocess.Popen([str(python), '-m', 'uvicorn', 'frontrow.server:app',
            '--host', '127.0.0.1', '--port', str(args.api_port)], cwd=ROOT / 'apps/api', env=env))
        deadline = time.monotonic() + 15
        while True:
            if processes[0].poll() is not None:
                raise RuntimeError('The API exited before becoming ready.')
            try:
                with urlopen(api_url + '/health', timeout=.5) as response:
                    if response.status == 200:
                        break
            except (URLError, TimeoutError):
                pass
            if time.monotonic() >= deadline:
                raise RuntimeError('The API did not become ready within 15 seconds.')
            time.sleep(.2)
        print(f'Retrieval configuration: {vector_config}. Probing local search (no model-provider calls)…', flush=True)
        for scope in ('general', 'uaeu'):
            print(f'  {scope}: {retrieval_probe(api_url, scope)} (search probe)', flush=True)
        print('Hybrid setup: /tmp/yaplab-vector-venv/bin/python, /tmp/yaplab-vector-model, '
              f'and {ROOT / "knowledge-base/local-vector"}; see docs/ai-for-good-local-kb.md '
              'for the complete setup. Explicit FRONTROW_POLICY_VECTOR_* settings override defaults. '
              'The worker falls back to lexical on failure; each search reports its actual mode.', flush=True)
        processes.append(subprocess.Popen([node, str(ROOT / 'frontend/node_modules/vite/bin/vite.js'), '--host', '127.0.0.1',
            '--port', str(args.ui_port), '--strictPort'], cwd=ROOT / 'frontend', env=env))
        mode = ('Recorded live exercise replay (read-only); no new model calls.' if args.replay_live
                else 'Fake classroom + scripted role proposals; no model or speech-provider requests.')
        print(f'\nYapLab demo: {ui_url}\n{mode}\nUse the demo deck and typed input. Ctrl+C stops both processes.\n', flush=True)
        while all(process.poll() is None for process in processes):
            time.sleep(.3)
        raise RuntimeError('A demo process exited; see its output above.')
    except KeyboardInterrupt:
        return 0
    except (OSError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    finally:
        for process in reversed(processes):
            if process.poll() is None:
                process.terminate()
        for process in processes:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


if __name__ == '__main__':
    sys.exit(main())
