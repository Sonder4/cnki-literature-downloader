#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import date
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from cnki_profiles import get_profile, infer_category, make_citation_key, normalize_text


def load_rows(path: Path) -> list[dict]:
    if path.suffix.lower() == ".json":
        return json.loads(path.read_text(encoding="utf-8"))
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def build_markdown_index(roots: list[Path]) -> list[Path]:
    indexed: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        indexed.extend(path for path in root.rglob("*.md") if path.is_file())
    return indexed


def find_markdown_for_title(title: str, candidates: list[Path]) -> Path | None:
    simple = normalize_text(title).replace(" ", "")
    for path in candidates:
        if simple and simple in path.stem.replace(" ", ""):
            return path
    return None


def parse_welcome_citation(text: str) -> str | None:
    match = re.search(r"【欢迎引用】\s*(.+)", text)
    if not match:
        return None
    line = normalize_text(match.group(1))
    return line.rstrip("。.") + "."


def parse_doi(text: str) -> str:
    match = re.search(r"DOI[:：]\s*([A-Za-z0-9./_-]+)", text, flags=re.I)
    return match.group(1) if match else ""


def parse_year(text: str) -> str:
    match = re.search(r"((19|20)\d{2})", text)
    return match.group(1) if match else ""


def parse_full_thesis_metadata(text: str) -> dict:
    metadata = {
        "author": "",
        "institution": "",
        "year": "",
        "city": "",
        "degree_level": "",
        "title": "",
    }
    title_match = re.search(r"论文题目[：:]\s*(.+)", text)
    if title_match:
        metadata["title"] = normalize_text(title_match.group(1))
    author_match = re.search(r"作者姓名\s*([^\n]+)", text)
    if author_match:
        metadata["author"] = normalize_text(author_match.group(1))
    institution_match = re.search(r"培养单位\s*([^\n]+)", text)
    if institution_match:
        metadata["institution"] = normalize_text(institution_match.group(1))
    metadata["year"] = parse_year(text)
    if "博士学位论文" in text:
        metadata["degree_level"] = "博士"
    elif "硕士学位论文" in text:
        metadata["degree_level"] = "硕士"
    return metadata


def normalize_authors(authors: str) -> str:
    text = normalize_text(authors)
    parts = [part.strip() for part in re.split(r"[;；]+", text) if part.strip()]
    return ", ".join(parts) if parts else text


def format_journal(row: dict, markdown_text: str) -> tuple[str, list[str], str]:
    direct = parse_welcome_citation(markdown_text)
    if direct:
        citation = direct
        if row.get("doi") or parse_doi(markdown_text):
            doi = row.get("doi") or parse_doi(markdown_text)
            if doi and doi not in citation:
                citation = citation.rstrip(".") + f". DOI: {doi}."
        return citation, [], "ready"

    authors = normalize_authors(row.get("authors", ""))
    title = normalize_text(row.get("title", ""))
    source = normalize_text(row.get("source", ""))
    year = parse_year(row.get("date", ""))
    volume = normalize_text(row.get("volume", ""))
    issue = normalize_text(row.get("issue", ""))
    pages = normalize_text(row.get("pages", ""))
    doi = row.get("doi") or parse_doi(markdown_text)

    missing = [name for name, value in (("authors", authors), ("title", title), ("source", source), ("year", year)) if not value]
    tail = year
    if volume and issue:
        tail += f", {volume}({issue})"
    elif volume:
        tail += f", {volume}"
    if pages:
        tail += f": {pages}"
    citation = f"{authors}. {title}[J]. {source}"
    if tail:
        citation += f", {tail}"
    citation = citation.rstrip(", ") + "."
    if doi:
        citation += f" DOI: {doi}."
    status = "ready" if not missing else "needs_completion"
    return citation, missing, status


def format_degree(row: dict, markdown_text: str) -> tuple[str, list[str], str]:
    parsed = parse_full_thesis_metadata(markdown_text)
    author = parsed["author"] or normalize_text(row.get("authors", ""))
    title = parsed["title"] or normalize_text(row.get("title", ""))
    institution = parsed["institution"] or normalize_text(row.get("source", "") or row.get("institution", ""))
    year = parsed["year"] or parse_year(row.get("date", ""))
    city = parsed["city"] or normalize_text(row.get("city", ""))
    doi = row.get("doi") or parse_doi(markdown_text)

    missing = [name for name, value in (("author", author), ("title", title), ("institution", institution), ("year", year)) if not value]
    if city:
        citation = f"{author}. {title}[D]. {city}: {institution}, {year}."
    else:
        citation = f"{author}. {title}[D]. {institution}, {year}."
    if doi:
        citation += f" DOI: {doi}."
    status = "ready" if not missing else "needs_completion"
    return citation, missing, status


def format_online(row: dict) -> tuple[str, list[str], str]:
    author = normalize_text(row.get("author", "") or row.get("source", ""))
    title = normalize_text(row.get("title", ""))
    access_date = normalize_text(row.get("access_date", "")) or f"{date.today():%Y-%m-%d}"
    url = normalize_text(row.get("url", "") or row.get("href", ""))
    year = parse_year(row.get("date", ""))
    missing = [name for name, value in (("title", title), ("author", author), ("url", url)) if not value]
    citation = f"{author}. {title}[EB/OL]."
    if year:
        citation += f" {year}."
    citation += f" [{access_date}]."
    if url:
        citation += f" \\url{{{url}}}."
    status = "ready" if not missing else "needs_completion"
    return citation, missing, status


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--profile", default="gbt7714-thesis-numeric")
    parser.add_argument("--content-root", action="append", type=Path, default=[])
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--include-bucket", action="append", default=[])
    args = parser.parse_args()

    rows = load_rows(args.input)
    profile = get_profile(args.profile)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    markdown_candidates = build_markdown_index(args.content_root)
    include_buckets = set(args.include_bucket)

    formatted_rows = []
    for row in rows:
        if include_buckets and row.get("bucket") not in include_buckets:
            continue
        title = row.get("title", "")
        markdown_path = find_markdown_for_title(title, markdown_candidates)
        markdown_text = markdown_path.read_text(encoding="utf-8", errors="ignore") if markdown_path else ""
        category = row.get("category") or infer_category(row)
        marker = row.get("ref_type", "")
        key = make_citation_key(title, row.get("date", ""))

        if marker == "EB/OL" or ("http" in row.get("href", "") and category == "journal" and not row.get("source")):
            citation, missing, status = format_online(row)
            ref_type = "EB/OL"
        elif category == "degree":
            citation, missing, status = format_degree(row, markdown_text)
            ref_type = "D"
        else:
            citation, missing, status = format_journal(row, markdown_text)
            ref_type = "J"

        if args.profile == "gbt7714-thesis-numeric":
            in_text = "[n]"
        else:
            in_text = "[n]"

        formatted_rows.append({
            "key": key,
            "title": title,
            "category": category,
            "ref_type": ref_type,
            "formatted_reference": citation,
            "in_text_style": in_text,
            "status": status if not missing else "needs_completion",
            "missing_fields": "; ".join(missing),
            "bucket": row.get("bucket", ""),
            "source_path": str(markdown_path) if markdown_path else "",
            "profile": profile["reference_profile"],
        })

    csv_path = args.output_dir / f"citation_candidates_{date.today():%Y%m%d}.csv"
    md_path = args.output_dir / f"参考文献格式清单_{date.today():%Y%m%d}.md"
    tex_path = args.output_dir / f"bibliography_ready_{date.today():%Y%m%d}.tex"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        fieldnames = list(formatted_rows[0].keys()) if formatted_rows else [
            "key", "title", "category", "ref_type", "formatted_reference", "in_text_style",
            "status", "missing_fields", "bucket", "source_path", "profile",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(formatted_rows)

    with md_path.open("w", encoding="utf-8") as handle:
        handle.write(f"# 参考文献格式清单（{date.today():%Y-%m-%d}）\n\n")
        handle.write(f"- Profile: `{profile['reference_profile']}`\n")
        handle.write(f"- Total rows: `{len(formatted_rows)}`\n\n")
        for idx, row in enumerate(formatted_rows, start=1):
            handle.write(f"## {idx}. {row['title']}\n\n")
            handle.write(f"- Key: `{row['key']}`\n")
            handle.write(f"- Type: `{row['ref_type']}`\n")
            handle.write(f"- Status: `{row['status']}`\n")
            if row["missing_fields"]:
                handle.write(f"- Missing fields: `{row['missing_fields']}`\n")
            if row["source_path"]:
                handle.write(f"- Source markdown: `{row['source_path']}`\n")
            handle.write(f"- Ready reference: `{row['formatted_reference']}`\n\n")

    with tex_path.open("w", encoding="utf-8") as handle:
        for row in formatted_rows:
            handle.write(f"\\bibitem{{{row['key']}}}\n{row['formatted_reference']}\n")

    print(json.dumps({"csv": str(csv_path), "md": str(md_path), "tex": str(tex_path)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
