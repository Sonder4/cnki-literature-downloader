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

from cnki_profiles import (
    JOURNAL_KEYWORDS,
    STRONG_ENGINEERING_UNIVERSITIES,
    TOP_INSTITUTIONS,
    get_profile,
    infer_category,
    normalize_text,
    split_cli_terms,
    topic_terms,
)


def load_rows(path: Path) -> list[dict]:
    if path.suffix.lower() == ".json":
        return json.loads(path.read_text(encoding="utf-8"))
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def to_int(value: str | int | None) -> int:
    text = str(value or "").replace(",", "").strip()
    return int(text) if text.isdigit() else 0


def year_value(text: str) -> int | None:
    match = re.search(r"(19|20)\d{2}", str(text or ""))
    return int(match.group(0)) if match else None


def percentile_score(value: int, population: list[int], max_score: int) -> int:
    cleaned = sorted(item for item in population if item >= 0)
    if not cleaned:
        return 0
    rank = sum(1 for item in cleaned if item <= value) / len(cleaned)
    if rank >= 0.9:
        return max_score
    if rank >= 0.7:
        return int(max_score * 0.8)
    if rank >= 0.4:
        return int(max_score * 0.55)
    return int(max_score * 0.25)


def source_quality_score(row: dict, category: str, max_score: int) -> int:
    source = normalize_text(row.get("source", "") or row.get("institution", ""))
    if category == "degree":
        if any(name in source for name in TOP_INSTITUTIONS):
            return max_score
        if any(name in source for name in STRONG_ENGINEERING_UNIVERSITIES):
            return int(max_score * 0.82)
        if "大学" in source:
            return int(max_score * 0.58)
        return int(max_score * 0.38)
    if any(keyword in source for keyword in JOURNAL_KEYWORDS):
        return max_score
    if "学报" in source:
        return int(max_score * 0.88)
    if source:
        return int(max_score * 0.56)
    return int(max_score * 0.3)


def recency_score(text: str, min_year: int, preferred_recent_years: int, max_score: int) -> int:
    year = year_value(text)
    if year is None:
        return int(max_score * 0.25)
    current_year = 2026
    if year < min_year or year > current_year:
        return 0
    if year >= current_year - preferred_recent_years + 1:
        return max_score
    if year >= current_year - preferred_recent_years - 3:
        return int(max_score * 0.78)
    if year >= current_year - preferred_recent_years - 7:
        return int(max_score * 0.55)
    return int(max_score * 0.3)


def relevance_score(text: str, query: str, priority_terms: list[str], max_score: int) -> int:
    lowered = normalize_text(text).lower()
    query_terms = topic_terms(query)
    priority_hits = sum(1 for term in priority_terms if term and term.lower() in lowered)
    query_hits = sum(1 for term in query_terms if term.lower() in lowered)
    score = priority_hits * int(max_score * 0.22) + query_hits * int(max_score * 0.12)
    if not priority_terms and not query_terms:
        return int(max_score * 0.55)
    return min(max_score, max(int(max_score * 0.18), score))


def discipline_fit_score(text: str, downrank_terms: list[str], exclude_terms: list[str], max_score: int) -> tuple[int, str]:
    lowered = normalize_text(text).lower()
    if any(term.lower() in lowered for term in exclude_terms):
        return 0, "命中排除词"
    if any(term.lower() in lowered for term in downrank_terms):
        return int(max_score * 0.4), "命中降权词"
    return max_score, ""


def bucket_for(score: int) -> str:
    if score >= 75:
        return "核心保留"
    if score >= 55:
        return "备选保留"
    return "低相关移除候选"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--category", choices=["journal", "degree", "auto"], default="auto")
    parser.add_argument("--profile", default="gbt7714-thesis-numeric")
    parser.add_argument("--topic", default="")
    parser.add_argument("--priority-term", action="append")
    parser.add_argument("--downrank-term", action="append")
    parser.add_argument("--exclude-term", action="append")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    rows = load_rows(args.input)
    profile = get_profile(args.profile)
    priority_terms = profile["priority_terms"] + split_cli_terms(args.priority_term) + topic_terms(args.topic)
    downrank_terms = profile["downrank_terms"] + split_cli_terms(args.downrank_term)
    exclude_terms = profile["exclude_terms"] + split_cli_terms(args.exclude_term)
    weights = profile["score_weights"]

    citations_population = [to_int(row.get("citations")) for row in rows]
    downloads_population = [to_int(row.get("downloads")) for row in rows]

    scored_rows = []
    for row in rows:
        category = args.category if args.category != "auto" else infer_category(row)
        search_context = args.topic or row.get("query", "")
        combined_text = " ".join(str(row.get(key, "")) for key in ("title", "authors", "source", "institution", "type", "query"))
        relevance = relevance_score(combined_text, search_context, priority_terms, weights["relevance"])
        source_quality = source_quality_score(row, category, weights["source_quality"])
        recency = recency_score(row.get("date", ""), profile["min_year"], profile["preferred_recent_years"], weights["recency"])
        citations = percentile_score(to_int(row.get("citations")), citations_population, weights["citations"])
        downloads = percentile_score(to_int(row.get("downloads")), downloads_population, weights["downloads"])
        discipline_fit, note = discipline_fit_score(combined_text, downrank_terms, exclude_terms, weights["discipline_fit"])
        total = relevance + source_quality + recency + citations + downloads + discipline_fit

        item = dict(row)
        item["category"] = category
        item["score"] = total
        item["bucket"] = bucket_for(total)
        item["score_relevance"] = relevance
        item["score_source_quality"] = source_quality
        item["score_recency"] = recency
        item["score_citations"] = citations
        item["score_downloads"] = downloads
        item["score_discipline_fit"] = discipline_fit
        item["note"] = note
        scored_rows.append(item)

    scored_rows.sort(key=lambda record: int(record.get("score", 0)), reverse=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8-sig") as handle:
        fieldnames = sorted({key for row in scored_rows for key in row.keys()})
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(scored_rows)

    print(json.dumps({"output": str(args.output), "rows": len(scored_rows)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
