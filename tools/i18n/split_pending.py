#!/usr/bin/env python3
"""Divide un archivo de pendientes en lotes para traducir."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("tools/i18n/pending.json"))
    parser.add_argument("--outdir", type=Path, default=Path("tools/i18n/pending"))
    parser.add_argument("--size", type=int, default=120)
    args = parser.parse_args()

    data = json.loads(args.input.read_text(encoding="utf-8"))
    items = data.get("items", [])
    context = data.get("context", {})

    args.outdir.mkdir(parents=True, exist_ok=True)
    for old in args.outdir.glob("pend_*.json"):
        old.unlink()

    n = 0
    for start in range(0, len(items), args.size):
        chunk = items[start : start + args.size]
        payload = {
            "items": chunk,
            "context": {i["zh"]: context.get(i["zh"], [])[:3] for i in chunk},
        }
        path = args.outdir / f"pend_{start // args.size:03d}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
        n += 1
    print(f"pendientes: {len(items)} -> {n} lotes en {args.outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
