#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from cnki_archive_caj import archive_caj
from cnki_profiles import infer_category


def load_rows(path: Path) -> list[dict]:
    if path.suffix.lower() == ".json":
        return json.loads(path.read_text(encoding="utf-8"))
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def run_browser_download(href: str, target_dir: Path, command: str = "download-detail-pdf") -> dict:
    cli = [
        sys.executable,
        str(SCRIPT_DIR / "cnki_browser_session.py"),
        command,
        "--href",
        href,
        "--target-dir",
        str(target_dir),
    ]
    result = subprocess.run(cli, capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


def list_files(folder: Path) -> dict[str, Path]:
    return {path.name: path for path in folder.iterdir() if path.is_file()}


def wait_for_new_files(folder: Path, before: dict[str, Path], timeout: int) -> list[Path]:
    start = time.time()
    last_seen: list[Path] = []
    while time.time() - start < timeout:
        current = list_files(folder)
        new_names = [name for name in current if name not in before]
        if new_names:
            last_seen = [current[name] for name in new_names]
        if last_seen and not list(folder.glob("*.crdownload")):
            stable = [path for path in last_seen if path.exists() and path.stat().st_size > 0]
            if stable:
                return stable
        time.sleep(1)
    return last_seen


def ensure_dirs(*paths: Path) -> None:
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)
        (path / "CAJ_仅备查").mkdir(exist_ok=True)


def relative_to_project(path: Path, project_root: Path) -> str:
    try:
        return str(path.relative_to(project_root))
    except ValueError:
        return str(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--journal-dir", type=Path, required=True)
    parser.add_argument("--degree-dir", type=Path, required=True)
    parser.add_argument("--output-log", type=Path, required=True)
    parser.add_argument("--poll-timeout", type=int, default=90)
    parser.add_argument("--retry-timeout", type=int, default=45)
    parser.add_argument("--pause-seconds", type=int, default=7)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    args = parser.parse_args()

    rows = load_rows(args.input)
    ensure_dirs(args.journal_dir, args.degree_dir)
    results: list[dict] = []

    for index, item in enumerate(rows, 1):
        category = item.get("category") or infer_category(item)
        target_dir = args.degree_dir if category == "degree" else args.journal_dir
        before = list_files(target_dir)
        record = dict(item)
        record["category"] = category
        record["status"] = "待处理"

        href = item.get("href", "")
        if not href:
            record["status"] = "缺少详情页链接"
            results.append(record)
            args.output_log.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
            continue

        try:
            payload = run_browser_download(href, target_dir, "download-detail-pdf")
            record["page_url"] = payload.get("page_url", "")
            record["detail_title"] = payload.get("title", "")
            record["buttons_seen"] = payload.get("buttons_seen", [])

            if payload.get("status") == "no_pdf_button":
                record["status"] = "无PDF下载按钮"
                results.append(record)
                args.output_log.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
                time.sleep(args.pause_seconds)
                continue

            new_files = wait_for_new_files(target_dir, before, args.poll_timeout)
            if not new_files:
                retry_payload = run_browser_download(href, target_dir, "retry-missing-download")
                record["retry_page_url"] = retry_payload.get("page_url", "")
                new_files = wait_for_new_files(target_dir, before, args.retry_timeout)
                if new_files:
                    record["retry_note"] = "initial click produced no stable file; retry succeeded"

            archived = archive_caj(target_dir, new_files or None)
            pdfs = [path for path in (new_files or []) if path.exists() and path.suffix.lower() == ".pdf"]
            if pdfs:
                record["status"] = "PDF已下载"
                record["files"] = [relative_to_project(path, args.project_root) for path in pdfs]
            elif archived:
                record["status"] = "仅CAJ备查"
                record["files"] = [relative_to_project(Path(path), args.project_root) for path in archived]
            else:
                record["status"] = "点击后未检测到文件"
                record["files"] = []
        except subprocess.CalledProcessError as exc:
            record["status"] = "异常"
            record["error"] = exc.stderr or str(exc)
        except Exception as exc:  # noqa: BLE001
            record["status"] = "异常"
            record["error"] = repr(exc)

        results.append(record)
        args.output_log.parent.mkdir(parents=True, exist_ok=True)
        args.output_log.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[{index}/{len(rows)}] {record.get('title', '')} -> {record['status']}", flush=True)
        time.sleep(args.pause_seconds)

    print(json.dumps({"log": str(args.output_log), "records": len(results)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
