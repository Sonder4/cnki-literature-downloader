#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from cnki_profiles import PROJECT_ROOT

LOCAL_BROWSER_HARNESS = PROJECT_ROOT / ".tools" / "browser-harness"


def build_harness_command() -> list[str]:
    override = os.environ.get("CNKI_BROWSER_HARNESS_CMD")
    if override:
        return shlex.split(override)
    if shutil.which("browser-harness"):
        return ["browser-harness"]
    if shutil.which("uv") and (LOCAL_BROWSER_HARNESS / "pyproject.toml").exists():
        return ["uv", "run", "--project", str(LOCAL_BROWSER_HARNESS), "browser-harness"]
    raise SystemExit(
        "browser-harness runtime not found. Install it on PATH or set CNKI_BROWSER_HARNESS_CMD."
    )


def extract_json(stdout: str) -> dict:
    lines = [line.strip() for line in stdout.splitlines() if line.strip()]
    for line in reversed(lines):
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue
    raise RuntimeError(f"failed to parse JSON from browser-harness output:\n{stdout}")


def run_harness(code: str) -> dict:
    command = build_harness_command() + ["-c", code]
    result = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "browser-harness failed\n"
            f"command: {' '.join(command)}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )
    return extract_json(result.stdout)


def code_prepare_session() -> str:
    return """
import json
ensure_real_tab()
print(json.dumps(page_info(), ensure_ascii=False))
""".strip()


def code_extract_results(query: str, limit: int, wait_seconds: int) -> str:
    payload = json.dumps(query, ensure_ascii=False)
    return f"""
import json
from urllib.parse import quote

query = {payload}
ensure_real_tab()
new_tab("https://kns.cnki.net/kns8s/defaultresult/index?kw=" + quote(query))
wait_for_load()
wait({wait_seconds})
rows = json.loads(js(r'''
(() => {{
  const out = [];
  for (const tr of Array.from(document.querySelectorAll('tbody tr'))) {{
    const cells = Array.from(tr.querySelectorAll('td')).map(td => (td.innerText || '').replace(/\\s+/g, ' ').trim());
    if (cells.length < 8) continue;
    const link = tr.querySelector('a.fz14, a[href*="abstract"], a');
    out.push({{
      title: link ? (link.innerText || '').trim() : (cells[1] || ''),
      authors: cells[2] || '',
      source: cells[3] || '',
      date: cells[4] || '',
      type: cells[5] || '',
      citations: cells[6] || '',
      downloads: cells[7] || '',
      href: link ? (link.href || '') : '',
      cells,
    }});
    if (out.length >= {limit}) break;
  }}
  return JSON.stringify(out);
}})()
''') or '[]')
print(json.dumps({{"query": query, "rows": rows, "page": page_info()}}, ensure_ascii=False))
""".strip()


def code_download_detail_pdf(href: str, target_dir: Path, wait_seconds: int) -> str:
    payload = json.dumps(href, ensure_ascii=False)
    target_payload = json.dumps(str(target_dir), ensure_ascii=False)
    return f"""
import json

href = {payload}
download_dir = {target_payload}

def visible_button_info():
    return json.loads(js(r'''
    (() => {{
      const buttons = Array.from(document.querySelectorAll('a,button'))
        .map(node => {{
          const text = (node.innerText || node.title || '').replace(/\\s+/g, ' ').trim();
          const rect = node.getBoundingClientRect();
          const style = window.getComputedStyle(node);
          return {{
            text,
            href: node.href || '',
            x: rect.left + rect.width / 2,
            y: rect.top + rect.height / 2,
            width: rect.width,
            height: rect.height,
            visible: rect.width > 0 && rect.height > 0 && style.display !== 'none' && style.visibility !== 'hidden',
          }};
        }})
        .filter(item => item.text);
      return JSON.stringify(buttons);
    }})()
    ''') or '[]')

def detail_meta():
    return json.loads(js(r'''
    (() => {{
      const title = (
        document.querySelector('h1') ||
        document.querySelector('.wx-tit h1') ||
        document.querySelector('.brief h1')
      );
      const text = (document.body.innerText || '').replace(/\\s+/g, ' ').trim();
      return JSON.stringify({{
        title: title ? title.innerText.replace(/\\s+/g, ' ').trim() : '',
        detail_excerpt: text.slice(0, 1600),
      }});
    }})()
    ''') or '{{}}')

ensure_real_tab()
cdp('Browser.setDownloadBehavior', behavior='allow', downloadPath=download_dir, eventsEnabled=True)
new_tab(href)
wait_for_load()
wait({wait_seconds})
buttons = visible_button_info()
meta = detail_meta()
candidate = next((item for item in buttons if item.get('visible') and 'PDF下载' in item.get('text', '')), None)
if candidate:
    click_at_xy(candidate['x'], candidate['y'])
    wait(2)
    status = 'clicked_pdf'
else:
    status = 'no_pdf_button'
print(json.dumps({{
  'status': status,
  'href': href,
  'page_url': page_info().get('url', ''),
  'title': meta.get('title', ''),
  'detail_excerpt': meta.get('detail_excerpt', ''),
  'button': candidate,
  'buttons_seen': [item for item in buttons if '下载' in item.get('text', '')],
}}, ensure_ascii=False))
""".strip()


def verify_downloads(target_dir: Path) -> dict:
    target_dir.mkdir(parents=True, exist_ok=True)
    return {
        "target_dir": str(target_dir),
        "pdf_files": sorted(str(path.name) for path in target_dir.glob("*.pdf")),
        "caj_files": sorted(str(path.name) for path in target_dir.glob("*.caj")),
        "crdownload_files": sorted(str(path.name) for path in target_dir.glob("*.crdownload")),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("prepare-session")

    extract_parser = subparsers.add_parser("extract-results")
    extract_parser.add_argument("--query", required=True)
    extract_parser.add_argument("--limit", type=int, default=30)
    extract_parser.add_argument("--wait-seconds", type=int, default=3)

    download_parser = subparsers.add_parser("download-detail-pdf")
    download_parser.add_argument("--href", required=True)
    download_parser.add_argument("--target-dir", required=True)
    download_parser.add_argument("--wait-seconds", type=int, default=2)

    retry_parser = subparsers.add_parser("retry-missing-download")
    retry_parser.add_argument("--href", required=True)
    retry_parser.add_argument("--target-dir", required=True)
    retry_parser.add_argument("--wait-seconds", type=int, default=2)

    verify_parser = subparsers.add_parser("verify-downloads")
    verify_parser.add_argument("--target-dir", required=True)

    args = parser.parse_args()

    if args.command == "prepare-session":
        payload = run_harness(code_prepare_session())
    elif args.command == "extract-results":
        payload = run_harness(code_extract_results(args.query, args.limit, args.wait_seconds))
    elif args.command in {"download-detail-pdf", "retry-missing-download"}:
        payload = run_harness(
            code_download_detail_pdf(args.href, Path(args.target_dir), args.wait_seconds)
        )
    else:
        payload = verify_downloads(Path(args.target_dir))

    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
