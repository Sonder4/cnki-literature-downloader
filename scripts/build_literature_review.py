#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from cnki_profiles import normalize_text


def load_rows(path: Path) -> list[dict]:
    if path.suffix.lower() == ".json":
        return json.loads(path.read_text(encoding="utf-8"))
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def build_markdown_index(roots: list[Path]) -> list[Path]:
    indexed: list[Path] = []
    for root in roots:
        if root.exists():
            indexed.extend(path for path in root.rglob("*.md") if path.is_file())
    return indexed


def find_markdown(title: str, candidates: list[Path]) -> Path | None:
    needle = normalize_text(title).replace(" ", "")
    for path in candidates:
        if needle and needle in path.stem.replace(" ", ""):
            return path
    return None


def extract_summary(text: str) -> str:
    patterns = [
        r"【摘要】(.+?)(?:Key words|关键词|主题词|# 1 引言)",
        r"# 摘要\s+(.+?)(?:# |\Z)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.S)
        if match:
            return normalize_text(match.group(1))[:260]
    return normalize_text(text[:260])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--topic", required=True)
    parser.add_argument("--content-root", action="append", type=Path, default=[])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    rows = load_rows(args.input)
    markdown_candidates = build_markdown_index(args.content_root)
    core = [row for row in rows if row.get("bucket") == "核心保留"]
    backup = [row for row in rows if row.get("bucket") == "备选保留"]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        handle.write(f"# {args.topic} 文献综述草稿\n\n")
        handle.write("## 1. 文献来源与筛选边界\n\n")
        handle.write("本稿依据 CNKI 检索结果、下载全文以及后续筛选表生成，用于形成中文文献综述初稿。正式进入论文正文前，仍需逐条完成原文定位、引文编号和章节级引用留痕。\n\n")
        handle.write("## 2. 核心文献脉络\n\n")
        if not core:
            handle.write("当前评分表中尚无 `核心保留` 文献，请先完成人工筛选。\n\n")
        for idx, row in enumerate(core, start=1):
            md_path = find_markdown(row.get("title", ""), markdown_candidates)
            summary = ""
            if md_path:
                summary = extract_summary(md_path.read_text(encoding="utf-8", errors="ignore"))
            handle.write(f"### 2.{idx} {row.get('title', '')}\n\n")
            handle.write(f"- 来源：{row.get('source', '')}\n")
            handle.write(f"- 类型：{row.get('type', '')}\n")
            handle.write(f"- 评分：{row.get('score', '')}\n")
            if summary:
                handle.write(f"- 摘要摘录：{summary}\n")
            handle.write("\n")

        handle.write("## 3. 备选文献与可补强方向\n\n")
        if not backup:
            handle.write("当前无 `备选保留` 文献。\n\n")
        for row in backup:
            handle.write(f"- {row.get('title', '')}（{row.get('source', '')}，{row.get('date', '')}）\n")
        handle.write("\n## 4. 写作提示\n\n")
        handle.write("- 优先使用核心期刊或高质量学位论文支撑研究现状与方法背景。\n")
        handle.write("- 学位论文更适合作为结构和实验写法参考，不宜单独承担高层结论。\n")
        handle.write("- 正式写作时，应把文献综述改写为连续段落，而不是保留本稿的提示式条目。\n")

    print(json.dumps({"output": str(args.output), "core": len(core), "backup": len(backup)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
