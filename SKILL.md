---
name: cnki-literature-downloader
description: Use when collecting Chinese academic literature from CNKI through a logged-in Chrome session, screening downloaded papers, or preparing CNKI references in reusable academic formats.
---

# CNKI Literature Downloader

## Overview

This skill packages a complete CNKI workflow around one stable entrypoint: search, download, full-text extraction, screening, literature-review drafting, and reference formatting.

The browser layer is internalized into the skill's own scripts. The operator should not need to hand-write `browser-harness -c '...'` snippets.

## When to Use

Use this skill when the task involves any of these:

- Searching CNKI with a logged-in browser session
- Downloading Chinese journal papers or degree theses from CNKI
- Preferring CNKI `PDF下载` over `CAJ`
- Screening downloaded Chinese literature after full-text extraction
- Generating CNKI download manifests or score tables
- Converting CNKI metadata into ready-to-paste reference entries
- Preparing `\bibitem{}` lines or Markdown/CSV references for academic writing

Do not use this skill when:

- The user needs non-CNKI sources only
- The browser is not already logged in to CNKI
- The task requires bypassing platform access control or bulk scraping beyond normal user permissions

## Operating Constraints

- Use the user's already-open and logged-in Chrome session through `browser-harness`.
- Do not export or copy browser cookie databases.
- Keep all downloads, manifests, and generated outputs inside the current project directory.
- Prefer `PDF下载` from the detail page. Treat `CAJ` only as fallback archival material.
- Respect site stability. The default rate limit is `10` download clicks per minute unless the user explicitly requests a stricter limit.
- Do not decide final relevance from title metadata alone. Full-text extraction is required before final screening.
- Reference formatting must follow the selected `profile`. The generic default profile in this repo is `gbt7714-thesis-numeric`.

## Quick Start

1. Read the active `profile` rules:
   - [references/scoring-rules.md](references/scoring-rules.md)
   - [references/browser-automation-contract.md](references/browser-automation-contract.md)
   - [references/reference-format-profiles.md](references/reference-format-profiles.md)
2. Prepare the browser session:
   ```bash
   python scripts/cnki_browser_session.py prepare-session
   ```
3. Extract candidate rows for one or more queries:
   ```bash
   python scripts/cnki_extract_candidates.py \
     --query "激光雷达 移动机器人 定位" \
     --query "移动机器人 自主导航" \
     --output-root "output/CNKI_20260503"
   ```
4. Score the candidates:
   ```bash
   python scripts/score_cnki_candidates.py \
     output/CNKI_20260503/cnki_candidates_20260503.json \
     --category auto \
     --profile gbt7714-thesis-numeric \
     --topic "移动机器人定位导航" \
     --output output/CNKI_20260503/评分表_20260503.csv
   ```
5. Download the queue:
   ```bash
   python scripts/cnki_download_batch.py \
     output/CNKI_20260503/cnki_candidates_20260503.json \
     --journal-dir output/CNKI_20260503/期刊 \
     --degree-dir output/CNKI_20260503/学位论文 \
     --output-log output/CNKI_20260503/cnki_download_log_20260503.json
   ```
6. After MinerU extraction, generate review and reference artifacts:
   ```bash
   python scripts/build_literature_review.py \
     output/CNKI_20260503/评分表_20260503.csv \
     --topic "移动机器人定位导航" \
     --content-root output/CNKI_20260503 \
     --output output/CNKI_20260503/文献综述草稿_20260503.md

   python scripts/format_cnki_references.py \
     output/CNKI_20260503/评分表_20260503.csv \
     --profile gbt7714-thesis-numeric \
     --content-root output/CNKI_20260503 \
     --output-dir output/CNKI_20260503/引用输出
   ```

## Workflow

### 1. Prepare a Profile

Choose a profile before starting:

- `gbt7714-thesis-numeric`: numeric, thesis-friendly Chinese bibliography output
- `generic-cn-academic`: general Chinese academic writing

Profile behavior is implemented in:

- [scripts/cnki_profiles.py](scripts/cnki_profiles.py)
- [references/reference-format-profiles.md](references/reference-format-profiles.md)

### 2. Search and Extract Candidates

Use [scripts/cnki_extract_candidates.py](scripts/cnki_extract_candidates.py) to:

- open CNKI result pages
- extract visible result rows
- persist JSON and CSV candidate sets
- normalize fields such as title, authors, source, date, type, citations, downloads, and detail-page URL

### 3. Score Before Download

Use [scripts/score_cnki_candidates.py](scripts/score_cnki_candidates.py) to:

- score by relevance, source quality, recency, citations, downloads, and discipline fit
- apply profile defaults plus optional term overrides
- classify candidates into `核心保留`, `备选保留`, and `低相关移除候选`

### 4. Download PDF-First

Use [scripts/cnki_download_batch.py](scripts/cnki_download_batch.py).

The batch downloader internally uses [scripts/cnki_browser_session.py](scripts/cnki_browser_session.py) to:

- attach to the logged-in browser
- open detail pages
- click visible `PDF下载`
- retry false negatives
- detect new files
- move `.caj` files into `CAJ_仅备查/`
- write an incremental JSON download log

### 5. Extract and Screen Full Text

After PDF download, run MinerU outside this skill or from your local workflow. Then use the scored table plus Markdown output to decide:

- which papers are core evidence
- which are background-only
- which should stay archived but not cited

### 6. Produce Review and Citation Artifacts

Use:

- [scripts/build_literature_review.py](scripts/build_literature_review.py) for a structured review draft
- [scripts/format_cnki_references.py](scripts/format_cnki_references.py) for formatted reference entries, `\bibitem{}` lines, and a citation candidate table

## Common Mistakes

- Treating CNKI result-page metadata as enough for final citation decisions
- Counting `CAJ` as equivalent to `PDF`
- Directly navigating to download URLs instead of using the visible detail-page button
- Forgetting to rerun screening after full-text extraction
- Generating references without checking the target profile

## Validation

- `prepare-session` must return live page info without browser errors
- No `.crdownload` should remain before reporting a download complete
- `评分表` buckets must match the final retained pool
- `bibliography_ready_*.tex` must contain valid `\bibitem{key}` lines
