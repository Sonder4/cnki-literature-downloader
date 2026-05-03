# CNKI Candidate Scoring Rules

This skill uses profile-driven scoring rather than a project-specific hard-coded topic list.

## Core Dimensions

Default dimensions:

- Relevance
- Source quality
- Recency
- Citations
- Downloads
- Discipline fit

Each profile sets the exact weights. The defaults live in:

- `scripts/cnki_profiles.py`

## Relevance

Score based on:

- overlap with the user topic
- overlap with the search query
- explicit priority terms
- title/abstract/source alignment with the intended writing problem

Relevance should favor papers that can support concrete claims, not just keyword matches.

## Source Quality

### Journals

Prefer:

- 学报
- 北大核心 / CSCD / EI style sources when known
- strong discipline journals

Heuristics in the script look for:

- `学报`
- `自动化`
- `机器人`
- `测绘`
- `控制`
- `导航`
- `雷达`
- `激光`
- strong university engineering journals

### Degree Theses

Prefer:

- 985 / 211 / 双一流 strong engineering universities
- 中国科学院大学 / 中科院系统
- strong regional engineering schools when topic relevance is high

## Recency

Default window:

- keep `2010` onward by default
- prefer the most recent `3-5` years
- retain older classics when they are still foundational

Profiles may adjust this window.

## Citations and Downloads

Use citations and downloads as auxiliary evidence rather than the primary decision variable.

- high counts can lift a borderline paper
- low counts should not automatically exclude recent work
- recent papers with short observation windows should be treated neutrally rather than punished

## Discipline Fit

This dimension is used to down-rank items that are academically valid but mismatched to the target writing task.

Examples:

- teaching reform papers
- product introductions
- course projects
- notices, conference announcements, or magazine-style non-research pieces

## Profile Overrides

The scoring script supports:

- `--profile`
- `--topic`
- repeated `--priority-term`
- repeated `--downrank-term`
- repeated `--exclude-term`

Use these when a specific writing task needs a narrower theme than the profile default.

## Buckets

Default output buckets:

- `核心保留`
- `备选保留`
- `低相关移除候选`

The thresholds are script-defined and intentionally conservative. A paper may still be moved between buckets after full-text reading.
