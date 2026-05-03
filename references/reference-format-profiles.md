# CNKI Reference Format Profiles

This file defines how the CNKI skill formats references after candidate screening.

## Profiles

### `gbt7714-thesis-numeric`

Target:

- Chinese academic writing with numeric in-text references
- Thesis or report workflows that prefer `\bibitem{}`-style output
- GB/T 7714-like bibliography generation with explicit type markers

Rules:

- In-text references are first-appearance numbered references
- When multiple references appear together, use independent bracketed numbers such as `[5][6]`
- Bibliography entries must preserve explicit type markers such as `[J]`, `[D]`, `[M]`, `[C]`, `[S]`, `[R]`, `[EB/OL]`
- LaTeX output must be compatible with `thebibliography` and `\bibitem{key}`
- URL-bearing online entries must preserve `\url{...}`

Common patterns:

- Journal: `作者. 题名[J]. 刊名, 年, 卷(期): 页码.`
- Degree thesis: `作者. 题名[D]. 地点: 单位, 年.`
- Monograph: `作者. 书名[M]. 版本. 出版地: 出版者, 年.`
- Conference: `作者. 题名[C]//会议名. 地点: 机构, 年: 页码.`
- Standard: `标准编号. 标准名称[S]. 发布地: 发布机构, 年.`
- Online document: `责任者. 题名[EB/OL]. [访问日期]. \url{...}.`

### `generic-cn-academic`

Target:

- Generic Chinese academic writing workflows
- CNKI-based local reference preparation without any repository-specific LaTeX assumptions

Rules:

- Preserve explicit type markers
- Prefer fully populated entries
- Mark rows with missing mandatory fields as `需补全`
- Output Markdown- and CSV-friendly reference lists even when LaTeX is not needed

## Mandatory Fields by Type

### `[J]` Journal

Required:

- authors
- title
- source
- year

Optional but strongly preferred:

- volume
- issue
- pages
- doi

### `[D]` Degree Thesis

Required:

- author
- title
- institution
- year

Optional but preferred:

- city
- degree level
- doi

### `[EB/OL]` Online Document

Required:

- title
- responsible party or site name
- access date
- url

## Output Files

The formatter should generate:

- `参考文献格式清单_<date>.md`
- `citation_candidates_<date>.csv`
- `bibliography_ready_<date>.tex`

## Readiness Status

Each formatted reference should be labeled as one of:

- `ready`: safe to paste after human review
- `needs_review`: major fields exist but style still needs inspection
- `needs_completion`: mandatory metadata is missing

## Usage Note

Generated bibliography text can be pasted into a local LaTeX project or adapted into another citation workflow, but that is only one step in a complete manuscript pipeline. The caller should still verify:

- first-appearance numbering
- in-text numbering consistency
- field completeness
- PDF/Word export compatibility in the target project
