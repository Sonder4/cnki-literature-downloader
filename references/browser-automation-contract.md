# CNKI Browser Automation Contract

This file defines the browser-side contract for the CNKI skill.

## Runtime

- Primary runtime: `browser-harness`
- Invocation is wrapped by `scripts/cnki_browser_session.py`
- Fallback runtime resolution:
  1. `CNKI_BROWSER_HARNESS_CMD` env override
  2. `browser-harness` on `PATH`
  3. `uv run --project .tools/browser-harness browser-harness`

## Allowed Browser Behaviors

- Attach to the user's already-running Chrome session
- Call `ensure_real_tab()` before navigation
- Open CNKI result pages and detail pages
- Use `Browser.setDownloadBehavior` to point downloads into a project-owned directory
- Use visible `PDF下载` buttons through `click_at_xy(...)`
- Use DOM reads through `js(...)` for metadata extraction

## Disallowed Behaviors

- Exporting or reading cookie databases from disk
- Reusing hidden or copied session stores
- Opening direct download links as the primary method when the site expects the detail-page flow
- Clicking faster than the configured rate limit

## Internal Subcommands

Implemented in `scripts/cnki_browser_session.py`:

- `prepare-session`
- `extract-results`
- `download-detail-pdf`
- `retry-missing-download`
- `verify-downloads`

## `extract-results`

Purpose:

- Navigate to a CNKI query results page
- Extract visible rows
- Return structured JSON rows

Expected output fields:

- `query`
- `rows[].title`
- `rows[].authors`
- `rows[].source`
- `rows[].date`
- `rows[].type`
- `rows[].citations`
- `rows[].downloads`
- `rows[].href`

## `download-detail-pdf`

Purpose:

- Open a CNKI detail page
- Find visible `PDF下载`
- Click it using coordinate interaction
- Return page-level click metadata for the local polling loop

Expected output fields:

- `status`
- `href`
- `page_url`
- `title`
- `button`
- `buttons_seen`
- `detail_excerpt`

`status` values:

- `clicked_pdf`
- `no_pdf_button`

## Retry Rule

If the first click succeeds visually but the local filesystem poll does not observe a new stable file, treat it as retryable. The batch downloader must:

1. Reopen the detail page
2. Click `PDF下载` again
3. Poll the target directory for at least `45` more seconds before failing

## Manual Handoff Conditions

Stop and ask the user to intervene when any of these occurs:

- CNKI login has expired
- A verification or anti-abuse page appears
- The page structure changes and no candidate rows can be extracted
- Only abnormal redirects are returned from detail pages
- Download permission is unavailable for the requested item

## Local Verification

`verify-downloads` should confirm:

- no `.crdownload` remains
- only project-local files are counted
- `.pdf` completion is tracked separately from `.caj` fallback archival
