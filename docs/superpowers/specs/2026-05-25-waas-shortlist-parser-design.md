# WaaS Shortlist Parser — Design

**Date:** 2026-05-25
**Status:** Approved (pending written-spec review)
**Component:** `job-hunter-agent`

---

## Goal

Build a parser for `workatastartup.com` (YC's "Work at a Startup") that turns a
pasted company-directory JSON dump into a ranked markdown shortlist of target
companies, oriented around Sergio's strategy: land a **direct** US startup role
at ~$140K, bypassing LATAM staffing platforms.

This replaces the outdated job-listing pipeline (Wellfound HTML, Prospera/HomeVision
reports) with a fresh, focused targeting tool.

## Non-Goals

- No live scraping / browser automation (WaaS is behind a YC login).
- No cover-note generation (this is company *targeting*, not applications).
- No Solaris DB writes (shortlist stays decoupled from the application tracker).
- No removal of the existing `--api` / `--theirstack` / HTML-processing code
  (left in place, unused; only the stale *data/leads* are removed).

---

## Data Acquisition

Manual paste/JSON dump (chosen over saved HTML and Playwright):

1. User logs into `workatastartup.com/companies`.
2. DevTools → Network → filter Fetch/XHR → find the response whose body is an
   array of companies (name, batch, team size, open roles).
3. Copy response → save as `job-hunter-agent/waas_dump.json`.

The exact endpoint/shape is confirmed against a real sample before `normalize()`
is finalized. `load_dump` is tolerant and logs discovered top-level keys when the
shape is unrecognized, so iterating on the real structure is fast.

---

## Architecture

**New module:** `job-hunter-agent/waas.py` — keeps the already-large `main.py`
(~950 lines) from growing further.

**CLI wiring:** `python main.py --waas [path]` (default path: `waas_dump.json`).

**Reused from `main.py`:** `load_profile`, `score_fit`, `fit_label`.

### Components

#### `load_dump(path) -> list[dict]`
Tolerant JSON reader. Handles the likely shapes:
- Algolia: `{"results": [{"hits": [...]}]}`
- Wrapped array: `{"companies": [...]}`
- Bare top-level list: `[...]`

On unrecognized shape, logs the top-level keys found and raises a clear error.
On missing file, prints exact instructions for grabbing the dump.

#### `Company` / `Job` dataclasses
```
Company: name, batch, team_size, location, remote (bool),
         tags (list[str]), one_liner, url, jobs (list[Job])
Job:     title, role_type, location, remote (bool),
         salary (str|None), equity (str|None), text (str)
```

#### `normalize(raw) -> Company`
Maps a raw company dict to the dataclass. **This is the single function tuned
against the real `waas_dump.json` sample.** Missing fields degrade gracefully
(empty string / None / empty list).

#### `score_company(company, profile) -> dict`
Company-level fit score blending four signals:

| Signal       | Weight | How |
|--------------|--------|-----|
| role_fit     | 0.40   | best `score_fit()` across the company's open eng roles (title + skills + location + salary text) |
| ai_product   | 0.20   | AI/LLM/agent/ML keyword hits in tags + one_liner |
| early_stage  | 0.20   | team size < ~30 and/or recent batch |
| intl_remote  | 0.20   | remote-friendly flag (proxy for "will hire from Argentina") |

Returns `{total, role_fit, ai_product, early_stage, intl_remote, best_role, reasons[]}`.

**Filtering:** companies with no role matching a primary target title, or with
zero stack overlap, are dropped before ranking.

Weights are module-level constants in `waas.py` (can graduate to `profile.yml`
later if tuning is needed — YAGNI for now).

#### `build_report(scored, profile, out_path)`
Writes `reports/waas-shortlist.md`:
- Header: date, source, candidate target.
- Ranked table: rank · company · batch · team · location · remote · best role · salary · fit%.
- Per-company sections for top N: one-line "why target," open roles, links.

#### `run(dump_path, profile) -> summary`
Orchestrates load → normalize → score → filter → report. Prints a console
summary. Emits `__coordinator_outputs__` JSON consistent with the other
`main.py` paths.

---

## Error Handling

- **Missing dump file** → message with exact steps to grab it from the Network tab.
- **Malformed JSON** → fail with the offending snippet.
- **Unknown shape** → log discovered top-level keys so `normalize()` can be adjusted.

---

## Testing

Repo currently has no tests. Keep this minimal:
- A trimmed fixture derived from the real `waas_dump.json`.
- One test asserting `load_dump → normalize → score_company → build_report`
  runs clean and produces a non-empty ranked report.

---

## Start-Fresh Cleanup (mechanical)

**Delete:**
- `Senior Full-Stack Engineer at Splink … .html` + its `_files/` directory
- `.processed` contents (clear)
- `reports/market-analysis-senior-frontend-2026.md`
- `reports/prospera-ai-fullstack-frontend.md`
- `reports/homevision-sr-frontend-engineer.md`

**Edit:**
- `config/profile.yml` → set `active_applications: []` (the two entries point at
  reports being deleted; everything else in `profile.yml` is untouched).

**Keep:**
- `CLAUDE.md`, `config/profile.yml` (minus active_applications), `roadmap-2month-120k.md`,
  `reports/linkedin-article-streaming-ui.md`
- Existing `--api` / `--theirstack` / HTML-processing code in `main.py` (unused, not deleted).

---

## Open Items

- `waas_dump.json` sample must be obtained before `normalize()` is finalized.
