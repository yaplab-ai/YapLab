#!/usr/bin/env python3
"""Run the complete synthetic demo locally using installed dependencies only."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--api-port', type=int, default=8765)
    parser.add_argument('--ui-port', type=int, default=5179)
    args = parser.parse_args()
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
    })
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
        processes.append(subprocess.Popen([node, str(ROOT / 'frontend/node_modules/vite/bin/vite.js'), '--host', '127.0.0.1',
            '--port', str(args.ui_port), '--strictPort'], cwd=ROOT / 'frontend', env=env))
        print(f'\nYapLab offline demo: {ui_url}\nFake classroom + scripted role proposals; no model or speech-provider requests.\nUse the demo deck and typed input. Ctrl+C stops both processes.\n', flush=True)
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
