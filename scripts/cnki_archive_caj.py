#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


def archive_caj(target_dir: Path, file_paths: list[Path] | None = None) -> list[str]:
    archive_dir = target_dir / "CAJ_仅备查"
    archive_dir.mkdir(parents=True, exist_ok=True)
    candidates = file_paths or list(target_dir.glob("*.caj"))
    moved: list[str] = []
    for path in candidates:
        if path.suffix.lower() != ".caj" or not path.exists():
            continue
        destination = archive_dir / path.name
        if destination.exists():
            destination = archive_dir / f"{path.stem}_{path.stat().st_mtime_ns}{path.suffix}"
        shutil.move(str(path), str(destination))
        moved.append(str(destination))
    return moved


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-dir", type=Path, required=True)
    parser.add_argument("files", nargs="*", type=Path)
    args = parser.parse_args()

    moved = archive_caj(args.target_dir, args.files or None)
    print(json.dumps({"archived": moved}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
