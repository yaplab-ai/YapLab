#!/usr/bin/env python3
"""Generate or check local ITU notebook inputs without downloading anything."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow invocation directly from apps/api without installing the project.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from frontrow.policy.export import export_bundle


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--institution', choices=('general', 'uaeu'), default='general',
                        help='source scope (default: general)')
    parser.add_argument('--output', type=Path, help='output directory (default: knowledge-base/itu-reference/<institution>)')
    parser.add_argument('--check', action='store_true', help='compare existing bundle with current corpus')
    args = parser.parse_args()
    output = args.output or (Path(__file__).resolve().parents[3] / 'knowledge-base' / 'itu-reference' / args.institution)
    try:
        export_bundle(output, check=args.check, institution=args.institution)
    except (OSError, ValueError, RuntimeError) as exc:
        print(f'Policy KB export failed: {exc}', file=sys.stderr)
        return 1
    print(f'Policy KB bundle {"verified" if args.check else "prepared"}: {output}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
