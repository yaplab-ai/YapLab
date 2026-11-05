"""Locally reviewed, bounded candidate gaps; no legal conclusions."""
from __future__ import annotations
import json
from pathlib import Path

_PATH = Path(__file__).with_name('gaps.json')

def load_gaps(scenario_id: str | None = None) -> dict:
    data = json.loads(_PATH.read_text(encoding='utf-8'))
    if scenario_id is not None:
        data['gaps'] = [item for item in data['gaps'] if item['scenario_id'] == scenario_id]
    return data
