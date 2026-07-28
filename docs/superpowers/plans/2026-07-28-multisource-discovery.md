# Multisource Recruitment Discovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add publicly accessible recruitment-software, employment-board, state-owned-platform and public-announcement sources while showing whether each job has an official or pending verification level.

**Architecture:** Source configuration declares the source type, name and public discovery URLs. Crawlers emit the existing `RawJob` fields plus source metadata; the pipeline chooses an official record over an otherwise-identical pending record and publishes a safe verification label. Only sources audited as anonymous public pages are enabled in GitHub Actions.

**Tech Stack:** Python 3.14, httpx, selectolax, Pydantic, PyYAML, pytest/respx, GitHub Actions and GitHub Pages.

---

## File structure

- `config/source_candidates.yaml` — first-wave source audit candidates.
- `config/sources.yaml` — enabled public source definitions with priority metadata.
- `src/autumn_jobs/models.py` — source type and verification fields.
- `src/autumn_jobs/normalization.py` — source-priority comparison helpers.
- `src/autumn_jobs/deduplication.py` — official-record precedence when merging duplicate jobs.
- `src/autumn_jobs/sources.py` — parse public announcement and job-board entries without credentials.
- `src/autumn_jobs/pipeline.py` — select button URLs and expose source/verification fields safely.
- `site/index.html`, `site/assets/app.js`, `site/assets/style.css` — verification badge and filter.
- `tests/test_models.py`, `tests/test_deduplication.py`, `tests/test_sources.py`, `tests/test_pipeline.py` — regression coverage.
- `docs/source-audit.json` — audit evidence for every candidate and enabled source.

### Task 1: Audit the exact first-wave public sources before enabling any of them

**Files:**
- Modify: `config/source_candidates.yaml`
- Modify: `docs/source-audit.json`
- Test: `tests/test_source_audit.py`

- [ ] **Step 1: Add the exact audit candidates**

Add these entries to `config/source_candidates.yaml`:

```yaml
  - id: bucea
    name: 北京建筑大学毕业生就业网
    url: https://job.bucea.edu.cn/front/zph.jspa?tid=113010
    group: university
  - id: guopinleida
    name: 国聘雷达
    url: https://guopinleida.com/
    group: public_aggregator
  - id: zhaopin_public
    name: 智联招聘公开校园招聘页
    url: https://www.zhaopin.com/
    group: job_board
  - id: job51_public
    name: 前程无忧校园招聘页
    url: https://campus.51job.com/
    group: job_board
  - id: liepin_public
    name: 猎聘公开职位页
    url: https://www.liepin.com/
    group: job_board
  - id: boss_public
    name: BOSS直聘公开职位页
    url: https://www.zhipin.com/
    group: job_board
```

- [ ] **Step 2: Run the audit command and capture evidence**

Run: `python scripts/audit_sources.py --candidates config/source_candidates.yaml --output docs/source-audit.json`

Expected: every candidate has a timestamp, final URL, access classification, page type and error code when unavailable. The command must not write cookies, response bodies or account data.

- [ ] **Step 3: Add a failing candidate-coverage assertion**

```python
def test_audit_covers_every_configured_candidate():
    candidates = yaml.safe_load(Path("config/source_candidates.yaml").read_text(encoding="utf-8"))
    candidate_ids = {row["id"] for row in candidates["candidates"]}
    audited_ids = {row.source_id for row in load_audit(Path("docs/source-audit.json"))}
    assert candidate_ids <= audited_ids
```

- [ ] **Step 4: Run the test and record the source decision**

Run: `python -m pytest tests/test_source_audit.py -q`

Expected: PASS. In `docs/source-audit.json`, set `note` to `enabled_public_list` only for sources returning a stable anonymous list/detail page; retain blocked/login/captcha sources as audit-only candidates.

- [ ] **Step 5: Commit audit evidence**

```bash
git add config/source_candidates.yaml docs/source-audit.json tests/test_source_audit.py
git commit -m "docs: audit public recruitment discovery sources"
```

### Task 2: Represent source type and verification status without exposing unnecessary data

**Files:**
- Modify: `src/autumn_jobs/models.py`
- Test: `tests/test_models.py`

- [ ] **Step 1: Write the failing model test**

```python
def test_raw_job_defaults_to_a_pending_public_announcement():
    job = RawJob(
        source_id="bucea", company="某设计院", title="建筑设计岗2027届校园招聘",
        location=["北京"], detail_url="https://job.bucea.edu.cn/front/zwxx.jspa?id=1",
        description="2027届本科，建筑学相关专业",
    )
    assert job.source_type == "public_article"
    assert job.verification_status == "pending"
    assert job.source_name is None
    assert job.official_apply_url is None
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_models.py::test_raw_job_defaults_to_a_pending_public_announcement -q`

Expected: FAIL because `RawJob` has no source metadata fields.

- [ ] **Step 3: Add typed source metadata**

```python
# Add after publish_date in RawJob and after alternate_sources in JobBusiness
source_type: Literal["official", "state_owned_platform", "university", "job_board", "public_article"] = "public_article"
verification_status: Literal["official", "verified", "pending"] = "pending"
source_name: str | None = None
official_apply_url: str | None = None
```

- [ ] **Step 4: Run the focused model test**

Run: `python -m pytest tests/test_models.py -q; python -m ruff check src/autumn_jobs/models.py tests/test_models.py`

Expected: PASS with no Ruff violations.

- [ ] **Step 5: Commit**

```bash
git add src/autumn_jobs/models.py tests/test_models.py
git commit -m "feat: add source verification metadata"
```

### Task 3: Preserve official records when a pending-source duplicate is discovered

**Files:**
- Modify: `src/autumn_jobs/deduplication.py`
- Test: `tests/test_deduplication.py`

- [ ] **Step 1: Write the failing precedence test**

```python
def test_deduplication_prefers_official_application_url():
    official = make_job(source_id="cscec8", detail_url="https://official.example/job/8")
    official = official.model_copy(update={"verification_status": "official", "source_type": "official"})
    pending = make_job(source_id="bucea", detail_url="https://job.bucea.edu.cn/front/zwxx.jspa?id=8")
    pending = pending.model_copy(update={"verification_status": "pending", "source_type": "university"})

    merged = deduplicate_jobs([pending, official])
    assert len(merged) == 1
    assert merged[0].verification_status == "official"
    assert merged[0].detail_url == "https://official.example/job/8"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_deduplication.py::test_deduplication_prefers_official_application_url -q`

Expected: FAIL because current selection depends on input order rather than verification status.

- [ ] **Step 3: Add a deterministic verification rank**

```python
VERIFICATION_RANK = {"official": 3, "verified": 2, "pending": 1}


def preferred_job(left: JobBusiness, right: JobBusiness) -> JobBusiness:
    left_rank = VERIFICATION_RANK[left.verification_status]
    right_rank = VERIFICATION_RANK[right.verification_status]
    return left if left_rank >= right_rank else right
```

Use `preferred_job` for duplicate fingerprints and retain the lower-priority detail URL in `alternate_sources`.

In `src/autumn_jobs/pipeline.py`, pass `raw.source_type`, `raw.verification_status`, `raw.source_name`, and `normalize_url(raw.official_apply_url)` into the matching `JobBusiness` fields inside `_to_business`.

- [ ] **Step 4: Run deduplication tests**

Run: `python -m pytest tests/test_deduplication.py -q; python -m ruff check src/autumn_jobs/deduplication.py tests/test_deduplication.py`

Expected: PASS with the official row selected regardless of input order.

- [ ] **Step 5: Commit**

```bash
git add src/autumn_jobs/deduplication.py tests/test_deduplication.py
git commit -m "fix: prefer official job records during deduplication"
```

### Task 4: Configure and crawl audited anonymous public announcement sources

**Files:**
- Modify: `config/sources.yaml`
- Modify: `src/autumn_jobs/sources.py`
- Test: `tests/test_sources.py`

- [ ] **Step 1: Write a failing metadata propagation test**

```python
def test_public_source_rows_inherit_configured_verification_metadata(tmp_path, respx_mock):
    config = tmp_path / "sources.yaml"
    config.write_text("""sources:
  - id: bucea
    company: 北京建筑大学毕业生就业网
    source_type: university
    verification_status: pending
    source_name: 北京建筑大学毕业生就业网
    url: https://job.bucea.edu.cn/front/zph.jspa?tid=113010
    archive_urls: []
    enabled: true
    max_items: 10
""", encoding="utf-8")
    respx_mock.get("https://job.bucea.edu.cn/front/zph.jspa?tid=113010").mock(
        return_value=httpx.Response(200, text='<a href="/front/zwxx.jspa?id=1">某设计院2027届建筑设计校招</a>')
    )
    respx_mock.get("https://job.bucea.edu.cn/front/zwxx.jspa?id=1").mock(
        return_value=httpx.Response(200, text="2027届本科，建筑学相关专业")
    )
    jobs, _ = crawl_configured_sources(config)
    assert jobs["bucea"][0].source_type == "university"
    assert jobs["bucea"][0].verification_status == "pending"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_sources.py::test_public_source_rows_inherit_configured_verification_metadata -q`

Expected: FAIL because generic `RawJob` construction ignores source metadata.

- [ ] **Step 3: Propagate approved configuration values**

```python
def source_metadata(source: dict[str, object]) -> dict[str, object]:
    return {
        "source_type": source.get("source_type", "public_article"),
        "verification_status": source.get("verification_status", "pending"),
        "source_name": source.get("source_name"),
        "official_apply_url": source.get("official_apply_url"),
    }
```

Pass `**source_metadata(source)` into both generic `RawJob(...)` construction sites. Add only the audit-approved candidates from Task 1 to `config/sources.yaml`, with `enabled: true`, their exact public list URL, `max_items: 50`, and `verification_status: pending`. Keep blocked/login/captcha candidates out of this file.

- [ ] **Step 4: Run crawler tests and a public crawl**

Run: `python -m pytest tests/test_sources.py -q; python scripts/crawl.py --all --summary artifacts/source-health.json`

Expected: all tests pass. Each enabled new source appears in `artifacts/source-health.json`; a source error does not delete prior jobs.

- [ ] **Step 5: Commit**

```bash
git add config/sources.yaml src/autumn_jobs/sources.py tests/test_sources.py docs/source-audit.json
git commit -m "feat: crawl audited public recruitment announcements"
```

### Task 5: Publish verification labels and an all/verified/pending filter

**Files:**
- Modify: `src/autumn_jobs/pipeline.py`
- Modify: `site/index.html`
- Modify: `site/assets/app.js`
- Modify: `site/assets/style.css`
- Test: `tests/test_pipeline.py`

- [ ] **Step 1: Write the failing public-payload test**

```python
def test_public_payload_exposes_safe_source_verification_fields(tmp_path):
    result = run_pipeline(
        {"bucea": [RawJob(
            source_id="bucea", company="某设计院", title="建筑设计岗2027届校园招聘",
            location=["北京"], detail_url="https://job.bucea.edu.cn/front/zwxx.jspa?id=1",
            description="2027届本科，建筑学相关专业", source_type="university",
            verification_status="pending", source_name="北京建筑大学毕业生就业网",
        )]}, {"bucea"}, tmp_path / "state", tmp_path / "site", date(2026, 7, 28)
    )
    row = json.loads(result.public_path.read_text(encoding="utf-8"))["jobs"][0]
    assert row["verification_status"] == "pending"
    assert row["source_type"] == "university"
    assert row["source_name"] == "北京建筑大学毕业生就业网"
    assert "description" not in row
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_pipeline.py::test_public_payload_exposes_safe_source_verification_fields -q`

Expected: FAIL because public payload omits verification fields.

- [ ] **Step 3: Expose safe fields and update the page UI**

Add `source_type`, `verification_status`, and `source_name` to `public_fields` in `_public_payload`. In `site/index.html`, add a select element with `id="verification-filter"` and options `全部状态`, `已核验`, `待核验`. In `site/assets/app.js`, map `official` and `verified` to `已核验`, map `pending` to `待核验`, filter by select value, and render the status as a badge next to the job title. In `site/assets/style.css`, add `.verification-official` and `.verification-pending` styles with readable contrast.

- [ ] **Step 4: Run tests and locally inspect the page data**

Run: `python -m pytest tests/test_pipeline.py -q; python -m ruff check src tests scripts; python scripts/crawl.py --all --summary artifacts/source-health.json`

Expected: tests pass, safe public JSON has no description/credentials, and the website has an all/verified/pending filter.

- [ ] **Step 5: Commit**

```bash
git add src/autumn_jobs/pipeline.py site/index.html site/assets/app.js site/assets/style.css tests/test_pipeline.py
git commit -m "feat: show source verification status"
```

### Task 6: Backfill, verify daily automation, and publish

**Files:**
- Modify: `data/state/jobs.json`
- Modify: `data/state/source_status.json`
- Modify: `site/data/jobs.json`
- Modify: `site/data/update_status.json`
- Create: `artifacts/source-health.json`

- [ ] **Step 1: Run the full backfill**

Run: `python scripts/crawl.py --all --summary artifacts/source-health.json`

Expected: output reports every enabled source and its discovered count. Only active, matching 2027 roles enter `site/data/jobs.json`.

- [ ] **Step 2: Validate published records**

```powershell
@'
import json
jobs = json.load(open("site/data/jobs.json", encoding="utf-8"))["jobs"]
assert all(row["apply_url"] or row["detail_url"] for row in jobs)
assert all(row["verification_status"] in {"official", "verified", "pending"} for row in jobs)
assert all("description" not in row for row in jobs)
print({"jobs": len(jobs), "pending": sum(row["verification_status"] == "pending" for row in jobs)})
'@ | python -
```

- [ ] **Step 3: Run full verification and commit only business-data changes**

Run: `python -m pytest -q; python -m ruff check src tests scripts; git diff --check`

Expected: all tests pass, Ruff passes, and no whitespace errors occur.

```bash
git add data/state/jobs.json data/state/source_status.json site/data/jobs.json site/data/update_status.json artifacts/source-health.json
git commit -m "data: add multisource 2027 job backfill"
```

- [ ] **Step 4: Push and manually run Pages deployment**

Run:

```bash
git push origin main
gh workflow run daily-update.yml --repo 19733152106xcy-collab/autumn-jobs
gh run watch --repo 19733152106xcy-collab/autumn-jobs --exit-status
```

Expected: Actions reports success and the public site presents verification badges and the new filter.

## Self-review

- Coverage: Task 1 audits the named job boards, employment board and aggregator; Tasks 2–5 implement source metadata, official precedence, anonymous public crawling and UI filtering; Task 6 verifies data and deployment.
- Boundaries: blocked, captcha, login-only and app-only sources remain audit-only. The crawler never stores credentials, raw HTML or full articles.
- Source safety: official links are always preferred; pending records retain their original public detail URL rather than fabricating a direct application link.
- Placeholder scan: no task contains a deferred marker, generic module name, or path requiring replacement.
- Type consistency: `source_type`, `verification_status`, `source_name`, `official_apply_url`, `source_metadata`, and `preferred_job` are defined before their use in later tasks.
