# Practical Daily Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make daily crawl status, formal-job focus, saved-state effects, and source health immediately understandable while improving relevant campaign matching.

**Architecture:** Keep the existing Python-to-static-JSON pipeline. Extend pure matching and health functions with tested behavior, then add small exported frontend helpers so filtering, reset behavior, summaries, and compact company rows stay testable without a browser backend.

**Tech Stack:** Python 3.12, pytest, Pydantic, vanilla JavaScript modules, Node assertions, GitHub Actions, GitHub Pages.

---

### Task 1: Formal-first filtering and reliable reset

**Files:**
- Modify: `tests/test_site.mjs`
- Modify: `site/assets/app.js`
- Modify: `site/index.html`

- [ ] Add failing assertions that `formal` includes full-time and mixed records but excludes pure internships, and that the reset state clears every filter.
- [ ] Run `node tests/test_site.mjs` and confirm the missing behavior fails.
- [ ] Add `defaultViewState`, `resetViewState`, and formal filtering; use the published update date for today filtering.
- [ ] Run `node tests/test_site.mjs` and confirm it passes.

### Task 2: Transparent counts and compact one-job companies

**Files:**
- Modify: `tests/test_site.mjs`
- Modify: `site/assets/app.js`
- Modify: `site/assets/style.css`
- Modify: `site/index.html`

- [ ] Add failing assertions for full/current/hidden/handled summary counts and one-job action rendering.
- [ ] Run `node tests/test_site.mjs` and confirm the assertions fail for missing helpers.
- [ ] Implement exported summary and company-row helpers, wire them into rendering, and style the compact summary.
- [ ] Run all Node tests and confirm they pass.

### Task 3: High-recall generic campaign matching without training-job noise

**Files:**
- Modify: `tests/test_matching.py`
- Modify: `src/autumn_jobs/matching.py`

- [ ] Add failing tests for a 2027 generic campaign with an eligible AI/product/design direction and for a teaching management trainee campaign that must remain excluded.
- [ ] Run the focused pytest tests and confirm both fail for the intended reasons.
- [ ] Implement generic-campaign body matching and education-training exclusions.
- [ ] Run focused and full matching tests.

### Task 4: Detect repeatedly empty sources

**Files:**
- Modify: `tests/test_source_status.py`
- Modify: `tests/test_sources.py`
- Modify: `src/autumn_jobs/sources.py`

- [ ] Add failing tests that the third consecutive empty discovery becomes suspect and that discovered counts reflect produced rows.
- [ ] Run the focused tests and confirm failure.
- [ ] Store `consecutive_empty`, mark only the third empty run suspect, and count produced source rows.
- [ ] Run focused tests and confirm they pass.

### Task 5: Regenerate, verify, and publish

**Files:**
- Modify: `data/state/jobs.json`
- Modify: `data/state/source_status.json`
- Modify: `site/data/jobs.json`
- Modify: `site/data/update_status.json`

- [ ] Run `python -m pytest -v`, `node tests/test_site.mjs`, and `node tests/frontend/test_page.mjs`.
- [ ] Run `python scripts/crawl.py --all --summary artifacts/source-health.json` and inspect job, company, internship, and source counts.
- [ ] Serve `site`, open the page, and verify desktop/mobile layout and saved-status behavior.
- [ ] Commit intentional changes, push the default branch, and verify the GitHub Actions deployment succeeds.

