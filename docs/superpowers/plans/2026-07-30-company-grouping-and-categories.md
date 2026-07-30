# 公司汇总与两类岗位 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让同公司岗位折叠展示，并将可投机会分为建筑类和其他类。

**Architecture:** 匹配层只根据岗位标题排除不匹配专项技术岗并输出 `job_group`；前端筛选后按公司聚合，点击展开显示各岗位与投递链接。

**Tech Stack:** Python、Pydantic、pytest、JavaScript ES modules、Node assert、GitHub Pages。

---

### Task 1: 精准排除与两类分类

**Files:** `config/keywords.yaml`, `src/autumn_jobs/models.py`, `src/autumn_jobs/matching.py`, `tests/test_matching.py`

- [ ] 写失败测试：`水暖工程岗` 对 2027 届本科建筑相关要求返回 `included=False`；`项目管理岗` 返回 `included=True`；建筑设计师返回 `job_group="architecture"`；AI 产品助理返回 `job_group="other"`。
- [ ] 运行 `python -m pytest -q tests/test_matching.py`，确认因缺少 `job_group` 且水暖岗仍保留而失败。
- [ ] 在 `keywords.yaml` 新增 `title_only_exclude`：水暖、暖通、给排水、机电、电气、结构、道路、隧道、安装预算、土建预算。
- [ ] 为 `MatchResult` 和 `JobBusiness` 添加 `job_group: Literal["architecture", "other"]`；`match_job()` 仅对岗位标题执行专项排除，直接/建筑相关匹配归为 `architecture`，跨行业匹配归为 `other`。
- [ ] 重跑 `python -m pytest -q tests/test_matching.py`，预期 PASS；提交 `feat: classify jobs and exclude unrelated specialties`。

### Task 2: 公开 JSON 元数据

**Files:** `src/autumn_jobs/pipeline.py`, `tests/test_pipeline.py`

- [ ] 在管道测试中断言公开岗位的 `job_group` 是 `architecture`。
- [ ] 运行 `python -m pytest -q tests/test_pipeline.py::test_pipeline_filters_deduplicates_and_writes_public_json`，预期 `KeyError: job_group`。
- [ ] 将匹配结果的 `job_group` 写入 `JobBusiness`，并加入公开字段列表。
- [ ] 重跑该测试，预期 PASS；提交 `feat: publish job group metadata`。

### Task 3: 公司折叠与筛选

**Files:** `site/index.html`, `site/assets/app.js`, `site/assets/style.css`, `tests/test_site.mjs`

- [ ] 写失败 Node 测试：两条公司名相同的岗位被 `groupJobsByCompany()` 归为一个组，组中包含两条岗位。
- [ ] 运行 `node tests/test_site.mjs`，预期缺少 `groupJobsByCompany` 导出。
- [ ] 导出 `groupJobsByCompany(jobs)`；`render()` 先过滤单岗位、再按公司分组，渲染公司概览行及默认隐藏的岗位明细。增加“全部岗位、建筑类、其他类”选择器。明细岗位保留机会类型、核验状态和独立投递链接。
- [ ] 重跑 `node tests/test_site.mjs`，预期 PASS；提交 `feat: group job listings by company`。

### Task 4: 重建、验证、发布

**Files:** `data/state/jobs.json`, `site/data/jobs.json`, `data/state/source_status.json`, `site/data/update_status.json`

- [ ] 运行 `python scripts/crawl.py --all --summary artifacts/source-health.json`；预期专项岗位不进入公开数据，且每条公开岗位有 `job_group`。
- [ ] 运行 `python -m pytest -q`、`python -m ruff check src tests scripts`、`node tests/test_site.mjs`；预期全部通过。
- [ ] 用脚本断言公开数据不含 `description`、每条均有 `job_group` 和至少一个投递或详情链接。
- [ ] 提交数据、推送 `main`，待 Pages 部署后读取线上 `data/jobs.json` 核验结果。
