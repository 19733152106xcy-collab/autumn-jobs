# Active 2027 Recruitment Backfill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Backfill every currently open, publicly accessible, matching 2027 campus-recruitment job from the configured sources and verified official recruitment portals, without publishing expired jobs or deleting results when a source fails.

**Architecture:** The crawler will discover concrete job-detail pages from configured public listing/archive pages, normalise them into `RawJob`, and attach an explicit official availability state. The pipeline will retain records only when their source did not complete successfully, so a healthy source can remove closed jobs while a failed source cannot erase prior jobs. Portal-specific adapters remain small and fixture-tested; the public site continues to read only the safe subset in `site/data/jobs.json`.

**Tech Stack:** Python 3.12, httpx, selectolax, Pydantic, PyYAML, pytest/respx, GitHub Actions, GitHub Pages.

---

## File structure

- `src/autumn_jobs/models.py` — add the explicit availability fields emitted by every crawler.
- `src/autumn_jobs/availability.py` — one pure active/closed decision function used before matching.
- `src/autumn_jobs/sources.py` — crawl configured listing and archive URLs with bounded pagination and report source health.
- `src/autumn_jobs/pipeline.py` — apply availability, preserve only failed-source records, and remove expired/closed results from state and public JSON.
- `src/autumn_jobs/adapters/cscec8.py` — discover C8 public job IDs from the real public client API/listing rather than a maintained ID list.
- `scripts/crawl.py` — pass successful source IDs to the pipeline and retain the existing Actions summary.
- `config/sources.yaml` — declare the public list/archive URLs and bounded item limits for each generic source.
- `config/cscec8.yaml` — remove manual IDs and retain only public adapter settings such as maximum page count.
- `tests/test_availability.py`, `tests/test_pipeline.py`, `tests/test_sources.py`, `tests/adapters/test_cscec8.py` — regression coverage for active-only output, safe failure preservation, listing discovery, and C8 parsing.
- `docs/source-audit.json` — append the exact public URL/API evidence, discovery count, and adapter decision for every source examined.

### Task 1: Encode official active/closed state before matching

**Files:**
- Create: `src/autumn_jobs/availability.py`
- Modify: `src/autumn_jobs/models.py`
- Test: `tests/test_availability.py`

- [ ] **Step 1: Write failing availability tests**

```python
from datetime import date

from autumn_jobs.availability import is_active_job
from autumn_jobs.models import RawJob


def make_job(**changes: object) -> RawJob:
    values: dict[str, object] = {
        "source_id": "official",
        "company": "某设计院",
        "title": "建筑设计岗2027届校园招聘",
        "location": ["西安"],
        "detail_url": "https://official.example/jobs/17",
        "description": "2027届本科，建筑学及相关专业",
    }
    values.update(changes)
    return RawJob(**values)


def test_expired_job_is_not_active():
    assert is_active_job(make_job(deadline=date(2026, 7, 26)), date(2026, 7, 27)) is False


def test_official_closed_marker_is_not_active():
    assert is_active_job(make_job(official_status="closed"), date(2026, 7, 27)) is False


def test_unknown_or_suspect_job_stays_active():
    assert is_active_job(make_job(official_status="unknown"), date(2026, 7, 27)) is True
    assert is_active_job(make_job(official_status="suspect"), date(2026, 7, 27)) is True
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_availability.py -q`

Expected: FAIL because `autumn_jobs.availability` does not exist.

- [ ] **Step 3: Add the model field and minimal decision function**

```python
# In src/autumn_jobs/models.py, inside RawJob
official_status: Literal["open", "closed", "unknown", "suspect"] = "unknown"
```

```python
# src/autumn_jobs/availability.py
from __future__ import annotations

from datetime import date

from autumn_jobs.models import RawJob


def is_active_job(job: RawJob, today: date) -> bool:
    if job.deadline is not None and job.deadline < today:
        return False
    return job.official_status != "closed"
```

- [ ] **Step 4: Run the focused test and full style checks**

Run: `python -m pytest tests/test_availability.py -q; python -m ruff check src/autumn_jobs/models.py src/autumn_jobs/availability.py`

Expected: all tests pass and Ruff reports no violations.

- [ ] **Step 5: Commit the atomic change**

```bash
git add src/autumn_jobs/models.py src/autumn_jobs/availability.py tests/test_availability.py
git commit -m "feat: classify closed and expired jobs"
```

### Task 2: Make pipeline removal safe for healthy sources and impossible for failed sources

**Files:**
- Modify: `src/autumn_jobs/pipeline.py`
- Modify: `scripts/crawl.py`
- Test: `tests/test_pipeline.py`

- [ ] **Step 1: Write failing pipeline regressions**

```python
def test_successful_source_removes_its_absent_job_but_failed_source_preserves_it(tmp_path):
    from datetime import date
    from autumn_jobs.models import RawJob
    from autumn_jobs.pipeline import run_pipeline

    old = RawJob(
        source_id="cadg", company="某设计院", title="建筑设计岗2027届校园招聘",
        location=["北京"], detail_url="https://official.example/jobs/1",
        description="2027届本科，建筑学及相关专业",
    )
    run_pipeline({"cadg": [old]}, {"cadg"}, tmp_path / "state", tmp_path / "site", date(2026, 7, 26))

    failed = run_pipeline({}, set(), tmp_path / "state", tmp_path / "site", date(2026, 7, 27))
    assert failed.jobs_count == 1

    succeeded = run_pipeline({"cadg": []}, {"cadg"}, tmp_path / "state", tmp_path / "site", date(2026, 7, 27))
    assert succeeded.jobs_count == 0


def test_pipeline_excludes_expired_raw_job(tmp_path):
    from datetime import date
    from autumn_jobs.models import RawJob
    from autumn_jobs.pipeline import run_pipeline

    expired = RawJob(
        source_id="cadg", company="某设计院", title="建筑设计岗2027届校园招聘",
        location=["北京"], detail_url="https://official.example/jobs/2",
        deadline=date(2026, 7, 26), description="2027届本科，建筑学及相关专业",
    )
    result = run_pipeline({"cadg": [expired]}, {"cadg"}, tmp_path / "state", tmp_path / "site", date(2026, 7, 27))
    assert result.jobs_count == 0
```

- [ ] **Step 2: Run the two new tests to verify they fail**

Run: `python -m pytest tests/test_pipeline.py::test_successful_source_removes_its_absent_job_but_failed_source_preserves_it tests/test_pipeline.py::test_pipeline_excludes_expired_raw_job -q`

Expected: FAIL because `run_pipeline` currently accepts no successful-source argument and does not consult availability.

- [ ] **Step 3: Change the pipeline signature and state merge**

```python
# In src/autumn_jobs/pipeline.py
from autumn_jobs.availability import is_active_job


def _to_business(raw: RawJob, today: date) -> JobBusiness | None:
    if not is_active_job(raw, today):
        return None
    matched = match_job(raw.title, raw.description)
    # keep the existing normalisation and JobBusiness construction below


def run_pipeline(
    source_jobs: dict[str, list[RawJob]],
    successful_source_ids: set[str],
    state_dir: Path,
    site_dir: Path,
    today: date,
) -> PipelineResult:
    # keep existing load/normalise/deduplicate code
    preserved = [job for job in previous if job.source_id not in successful_source_ids]
    combined = deduplicate_jobs(preserved + current)
```

```python
# In scripts/crawl.py, immediately before run_pipeline
successful_source_ids = {row.source_id for row in health if row.status == "ok"}
result = run_pipeline(source_jobs, successful_source_ids, Path("data/state"), Path("site"), today)
```

Update every existing `run_pipeline(...)` test call to pass the set of source IDs whose mocked crawls succeeded.

- [ ] **Step 4: Run pipeline and crawler tests**

Run: `python -m pytest tests/test_pipeline.py tests/test_availability.py -q; python -m ruff check src/autumn_jobs/pipeline.py scripts/crawl.py`

Expected: all selected tests pass and Ruff reports no violations.

- [ ] **Step 5: Commit the atomic change**

```bash
git add src/autumn_jobs/pipeline.py scripts/crawl.py tests/test_pipeline.py
git commit -m "fix: preserve jobs only when a source fails"
```

### Task 3: Crawl all configured public listing and archive pages within explicit limits

**Files:**
- Modify: `config/sources.yaml`
- Modify: `src/autumn_jobs/sources.py`
- Modify: `tests/test_sources.py`

- [ ] **Step 1: Write a failing listing-page traversal test**

```python
def test_extract_listing_urls_combines_root_and_declared_archive_urls():
    from autumn_jobs.sources import configured_listing_urls

    source = {
        "url": "https://official.example/campus",
        "archive_urls": [
            "https://official.example/campus?page=2",
            "https://official.example/campus?page=3",
        ],
    }

    assert configured_listing_urls(source) == [
        "https://official.example/campus",
        "https://official.example/campus?page=2",
        "https://official.example/campus?page=3",
    ]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_sources.py::test_extract_listing_urls_combines_root_and_declared_archive_urls -q`

Expected: FAIL because `configured_listing_urls` does not exist.

- [ ] **Step 3: Implement deterministic URL traversal and configuration validation**

```python
# In src/autumn_jobs/sources.py
def configured_listing_urls(source: dict[str, object]) -> list[str]:
    urls = [str(source["url"]), *(str(url) for url in source.get("archive_urls", []))]
    return list(dict.fromkeys(urls))
```

Replace the single `root = client.get(source["url"])` block with a loop over `configured_listing_urls(source)`. For each successful response, call `extract_job_links(str(response.url), response.text, max_items)`, retain unique `detail_url` values, then fetch at most `max_items` unique details in total. Set `SourceHealth.discovered` to the number of unique detail URLs. If any listing request returns an HTTP error, mark the entire source failed and return no partial result for that source; this ensures Task 2 preserves its prior jobs.

Add `archive_urls: []` to every source entry in `config/sources.yaml`. For each source with an audited public search/list page, place that exact page URL in `archive_urls`; do not generate page numbers that were not observed on the public site.

- [ ] **Step 4: Run source tests and one real non-writing crawl**

Run: `python -m pytest tests/test_sources.py -q; python scripts/crawl.py --summary artifacts/source-health.json`

Expected: unit tests pass; the command prints one health row per enabled source and does not contain credentials, response HTML, cookies, or tokens.

- [ ] **Step 5: Record audit evidence and commit**

For each enabled source, append one JSON object to `docs/source-audit.json` with these exact keys: `id`, `checked_at`, `listing_urls`, `public_access`, `discovered`, `adapter`, and `notes`. `public_access` must be `true` only after a 200 response without login/captcha; `adapter` must be either `generic` or `not_implemented`.

```bash
git add config/sources.yaml src/autumn_jobs/sources.py tests/test_sources.py docs/source-audit.json
git commit -m "feat: crawl audited public listing pages"
```

### Task 4: Replace the C8 manual ID list with public list discovery

**Files:**
- Modify: `config/cscec8.yaml`
- Modify: `src/autumn_jobs/adapters/cscec8.py`
- Modify: `tests/adapters/test_cscec8.py`
- Modify: `scripts/crawl.py`

- [ ] **Step 1: Capture and fixture the public C8 company/index responses**

The C8 public React site exposes its unit directory at `https://job.cscec8b.com.cn/cscec8b/data/names.json`. Each directory entry includes a `jobApi` value such as `/api/job/getIndexPublishJob.json?company=28`; request that value from `https://job.cscec8b.com.cn` to obtain the published-job list for that unit. Record the directory URL and every non-empty `jobApi` URL in the `cscec8` object in `docs/source-audit.json`. Save a minimal redacted directory body containing two `jobApi` values and a minimal job-list body containing one open and one closed item as `C8_DIRECTORY_BODY` and `C8_LIST_BODY` constants in `tests/adapters/test_cscec8.py`; neither fixture may contain cookies, authorization headers, or applicant information.

- [ ] **Step 2: Write the failing discovery test**

```python
@respx.mock
def test_crawl_cscec8_jobs_discovers_open_ids_before_fetching_details():
    from autumn_jobs.adapters.cscec8 import crawl_cscec8_jobs

    respx.get("https://job.cscec8b.com.cn/cscec8b/data/names.json").mock(
        return_value=httpx.Response(200, text=C8_DIRECTORY_BODY)
    )
    respx.get("https://job.cscec8b.com.cn/api/job/getIndexPublishJob.json?company=28").mock(
        return_value=httpx.Response(200, text=C8_LIST_BODY)
    )
    respx.get("https://job.cscec8b.com.cn/recruitment/job/detail/id/3001").mock(
        return_value=httpx.Response(200, text=DETAIL_HTML)
    )
    respx.get("https://job.cscec8b.com.cn/headhunter/showjobdesc/id/3001").mock(
        return_value=httpx.Response(200, text="<p>2027届本科，建筑学相关专业</p>")
    )

    jobs = crawl_cscec8_jobs()
    assert [job.source_job_id for job in jobs] == ["3001"]
```

- [ ] **Step 3: Run the discovery test to verify it fails**

Run: `python -m pytest tests/adapters/test_cscec8.py::test_crawl_cscec8_jobs_discovers_open_ids_before_fetching_details -q`

Expected: FAIL because `crawl_cscec8_jobs` currently requires a static `job_ids` argument.

- [ ] **Step 4: Implement list discovery and remove static IDs**

Implement `discover_cscec8_jobs(client: httpx.Client, settings: dict[str, object]) -> list[tuple[str, str]]` in `src/autumn_jobs/adapters/cscec8.py`. It must request `https://job.cscec8b.com.cn/cscec8b/data/names.json`, request every non-empty `jobApi` listed there, return only IDs marked open by the official list, and return `(job_id, detail_url)` pairs in source order. Change `crawl_cscec8_jobs()` to load `config/cscec8.yaml`, call discovery, then reuse the existing detail/description parsing for every discovered ID. Change `config/cscec8.yaml` to this shape:

```yaml
max_pages: 20
max_companies: 100
```

Change `scripts/crawl.py` to call `crawl_cscec8_jobs(Path("config/cscec8.yaml"))`, delete `load_cscec8_job_ids`, and update imports/tests accordingly. Preserve a failed `cscec8` health result when the list request errors or returns an invalid response.

- [ ] **Step 5: Run adapter and crawler checks, then commit**

Run: `python -m pytest tests/adapters/test_cscec8.py -q; python -m ruff check src/autumn_jobs/adapters/cscec8.py scripts/crawl.py`

Expected: all adapter tests pass, including closed-item exclusion and detail parsing.

```bash
git add config/cscec8.yaml src/autumn_jobs/adapters/cscec8.py scripts/crawl.py tests/adapters/test_cscec8.py docs/source-audit.json
git commit -m "feat: discover active C8 jobs from official listings"
```

### Task 5: Execute the active-only backfill, inspect output, and publish through Actions

**Files:**
- Modify: `data/state/jobs.json` only when active business data changes
- Modify: `site/data/jobs.json` only when active business data changes
- Modify: `site/data/update_status.json` only when active business data changes
- Modify: `data/state/source_status.json`
- Create: `artifacts/source-health.json`

- [ ] **Step 1: Run the full crawler locally**

Run: `python scripts/crawl.py --all --summary artifacts/source-health.json`

Expected: JSON output contains a health row for every enabled generic source and every enabled official adapter; no source failure removes jobs that were previously retained from that source.

- [ ] **Step 2: Validate active-only public data and official links**

Run:

```powershell
@'
import json
from datetime import date
jobs = json.load(open("site/data/jobs.json", encoding="utf-8"))["jobs"]
assert all(job["status"] == "active" for job in jobs)
assert all(not job["deadline"] or job["deadline"] >= date.today().isoformat() for job in jobs)
assert all(job["apply_url"] or job["detail_url"] for job in jobs)
assert all("description" not in job for job in jobs)
print({"active_jobs": len(jobs), "companies": len({job["company"] for job in jobs})})
'@ | python -
```

Expected: process exits 0 and prints the active job/company count.

- [ ] **Step 3: Review source health before committing data**

Run: `Get-Content -Raw artifacts/source-health.json; Get-Content -Raw data/state/source_status.json`

Expected: each failing or suspect source includes an error/status and remains visible; do not commit an empty result for a source whose prior successful count was non-zero.

- [ ] **Step 4: Run full checks and commit only meaningful public-data changes**

Run: `python -m pytest -q; python -m ruff check src tests scripts; git status --short`

Expected: all tests and Ruff pass. Include `data/state/jobs.json`, `site/data/jobs.json`, and `site/data/update_status.json` only if the public job list changed; `data/state/source_status.json` may record this run's health without triggering Pages publication by itself.

```bash
git add data/state/jobs.json data/state/source_status.json site/data/jobs.json site/data/update_status.json artifacts/source-health.json
git commit -m "data: backfill active 2027 recruitment jobs"
```

- [ ] **Step 5: Push and run the existing manual GitHub Actions workflow**

Run:

```bash
git push origin main
gh workflow run daily-update.yml --repo 19733152106xcy-collab/autumn-jobs
gh run watch --repo 19733152106xcy-collab/autumn-jobs --exit-status
```

Expected: the workflow completes successfully, publishes only when public jobs differ, and deploys the Pages artifact. Verify `https://19733152106xcy-collab.github.io/autumn-jobs/` shows the same count as `site/data/jobs.json`.

## Self-review

- Spec coverage: Tasks 1 and 2 implement active-only rules and source-failure preservation; Task 3 expands configured public listings; Task 4 replaces the six-entry C8 bootstrap with official discovery from every public C8 unit; Task 5 backfills, checks official links, runs tests, and verifies Actions/Pages.
- Data safety: no task saves raw HTML, credentials, cookies, request headers, personal identity, or an archive of expired jobs. All public output continues to omit `description`.
- Scope control: each source is audited before an adapter is added. Public-but-unauthenticated sources are included; login, captcha, mini-program, and referral-only systems are explicitly excluded rather than guessed.
- Placeholder scan: no task contains TBD markers, template paths, or names intended for later substitution.
- Type consistency: `RawJob.official_status`, `is_active_job`, `successful_source_ids`, `configured_listing_urls`, and `discover_cscec8_jobs` are defined before later tasks rely on them.
