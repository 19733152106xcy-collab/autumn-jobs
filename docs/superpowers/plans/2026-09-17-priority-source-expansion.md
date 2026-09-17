# 待遇优先与高价值来源扩展 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 接入稳定的高价值公开来源，并让每日抓取结果能说明抓到、入库和筛除的数量。

**Architecture:** 新增独立的华中科技大学就业网适配器，输出统一 `RawJob`；流水线计算每个来源的入库统计，并将公开摘要写入 `site/data/update_status.json`。匹配与评分继续以配置文件驱动，不暴露岗位正文。

**Tech Stack:** Python 3.12、httpx、selectolax、Pydantic、Pytest、原生 JavaScript。

---

### Task 1: 高校就业网适配器

**Files:**
- Create: `src/autumn_jobs/adapters/hust.py`
- Create: `config/hust.yaml`
- Create: `tests/adapters/test_hust.py`
- Modify: `scripts/crawl.py`

- [ ] **Step 1: Write the failing adapter test**

```python
def test_crawl_hust_reads_listing_and_public_detail():
    jobs = crawl_hust_jobs({"pages": 1, "max_items": 5})
    assert jobs[0].source_id == "hust"
    assert jobs[0].source_type == "university"
    assert jobs[0].verification_status == "verified"
```

- [ ] **Step 2: Run the adapter test and verify it fails because the module does not exist.**

Run: `.\\.venv\\Scripts\\python.exe -m pytest tests/adapters/test_hust.py -v`

- [ ] **Step 3: Implement a minimal adapter**

Use `ul.nytzlist a[href*='/zpinfo1/']` for listing links and `.content` for detail text. Derive the company from the campaign title, retain the public details URL, and set source fields to `hust`, `university`, `verified`, and `华中科技大学就业信息网`.

- [ ] **Step 4: Run the adapter test and verify it passes.**

- [ ] **Step 5: Register the adapter in `scripts/crawl.py` and add `config/hust.yaml`.**

### Task 2: 可解释的每日入库统计

**Files:**
- Modify: `src/autumn_jobs/models.py`
- Modify: `src/autumn_jobs/pipeline.py`
- Modify: `scripts/crawl.py`
- Modify: `tests/test_pipeline.py`

- [ ] **Step 1: Write a failing pipeline test**

```python
assert result.source_counts["hust"] == {"discovered": 2, "included": 1, "excluded": 1}
```

- [ ] **Step 2: Run the test and verify `PipelineResult` has no `source_counts` attribute.**

- [ ] **Step 3: Implement source-level counts**

Count each raw job once before matching; count an included item only after availability and matching succeed. Preserve duplicate accounting separately. Write `today_added` and `source_counts` into the public update-status JSON whenever public data changes or the status file is refreshed.

- [ ] **Step 4: Run the focused test and verify it passes.**

### Task 3: 待遇优先的匹配与评分配置

**Files:**
- Modify: `config/keywords.yaml`
- Modify: `config/quality_employers.yaml`
- Modify: `config/scoring.yaml`
- Modify: `tests/test_matching.py`
- Modify: `tests/test_scoring.py`

- [ ] **Step 1: Write failing tests**

```python
assert match_job("城市更新设计管理岗", "2027届本科，建筑学相关专业").included
assert not match_job("水暖工程师", "2027届本科，工程类相关专业").included
```

- [ ] **Step 2: Run the focused tests and verify the new cases fail before configuration changes.**

- [ ] **Step 3: Add focused terms and salary/platform profiles**

Add design management, city operation, international engineering, building technology and digital solution wording. Add only named high-quality employers and state whether salary is an estimate; no salary number is invented.

- [ ] **Step 4: Run matching and scoring tests and verify they pass.**

### Task 4: End-to-end crawl and publish data

**Files:**
- Modify: `data/state/jobs.json` (generated)
- Modify: `site/data/jobs.json` (generated)
- Modify: `site/data/update_status.json` (generated)
- Modify: `data/state/source_status.json` (generated)

- [ ] **Step 1: Run `.\\.venv\\Scripts\\python.exe scripts/crawl.py --all --summary artifacts/source-health.json`.**
- [ ] **Step 2: Inspect the source health and public payload; verify actual current positions from the new source are present only when they meet filters.**
- [ ] **Step 3: Run `.\\.venv\\Scripts\\python.exe -m pytest -v`, `.\\.venv\\Scripts\\python.exe -m ruff check .`, and `node tests/frontend/test_page.mjs`.**
- [ ] **Step 4: Commit the completed, tested update.**
