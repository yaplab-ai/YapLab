"""Score saved full audit export(s) or round(s); no model or network calls."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from frontrow.policy.outcomes import markdown, score

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('inputs', nargs='+', type=Path, help='Full audit JSON exports or saved rounds, one per scenario/stage')
    parser.add_argument('--output', required=True, type=Path, help='Markdown comparison table')
    parser.add_argument('--json-output', type=Path, help='Optional full structured comparison')
    args = parser.parse_args()
    try:
        data = [json.loads(path.read_text(encoding='utf-8')) for path in args.inputs]
        report = score(data)
        args.output.write_text(markdown(report), encoding='utf-8')
        if args.json_output:
            args.json_output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(2, f'Unable to score: {exc}\n')
    print(f"Scored {len(report['results'])} scenario/stage/role rows; missing rounds are reported as misses.")
    return 0
if __name__ == '__main__':
    raise SystemExit(main())
