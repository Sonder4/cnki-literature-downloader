#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent


def run_browser_extract(query: str, limit: int) -> dict:
    command = [
        sys.executable,
        str(SCRIPT_DIR / "cnki_browser_session.py"),
        "extract-results",
        "--query",
        query,
        "--limit",
        str(limit),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


def write_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["query", "title", "authors", "source", "date", "type", "citations", "downloads", "href"]
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows([{key: row.get(key, "") for key in fieldnames} for row in rows])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", action="append", required=True, help="repeatable CNKI query")
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--basename", default=None)
    args = parser.parse_args()

    output_root = args.output_root
    output_root.mkdir(parents=True, exist_ok=True)
    suffix = args.basename or f"cnki_candidates_{date.today():%Y%m%d}"
    json_path = output_root / f"{suffix}.json"
    csv_path = output_root / f"{suffix}.csv"

    rows: list[dict] = []
    for query in args.query:
        payload = run_browser_extract(query, args.limit)
        for row in payload.get("rows", []):
            row = dict(row)
            row["query"] = payload.get("query", query)
            rows.append(row)

    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    write_csv(rows, csv_path)
    print(json.dumps({"json": str(json_path), "csv": str(csv_path), "rows": len(rows)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
