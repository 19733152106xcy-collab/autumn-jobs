# 岗位状态记忆 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让用户在静态岗位库中标记已投递或不感兴趣的单个岗位，并将已标记岗位默认收起。

**Architecture:** 前端 `localStorage` 以岗位指纹保存状态；渲染前将数据分为待处理、已投递和不感兴趣三组。公司汇总仅对每个状态组内岗位执行，不修改公开岗位 JSON。

**Tech Stack:** JavaScript ES modules、Node assert、浏览器 localStorage、GitHub Pages。

---

### Task 1: 状态存储与过滤函数

**Files:** `site/assets/app.js`, `tests/test_site.mjs`

- [ ] 写失败测试：`setJobStatus(statuses, "job-1", "applied")` 返回含 `job-1: "applied"` 的对象；`partitionJobsByStatus()` 将三条岗位分为 pending、applied、not_interested 三组；传入 `null` 撤销状态。
- [ ] 运行 `node tests/test_site.mjs`，预期缺少导出函数。
- [ ] 导出纯函数 `setJobStatus(statuses, fingerprint, status)` 和 `partitionJobsByStatus(jobs, statuses)`；使用 `fingerprint` 为键，不直接在岗位对象写状态。
- [ ] 重跑 Node 测试，预期 PASS；提交 `feat: add local job status state`。

### Task 2: 标记、折叠与撤销界面

**Files:** `site/index.html`, `site/assets/app.js`, `site/assets/style.css`, `tests/test_site.mjs`

- [ ] 写失败测试：标记为 applied 的岗位不属于 `partitionJobsByStatus(...).pending`。
- [ ] 运行 `node tests/test_site.mjs`，预期断言失败。
- [ ] 在岗位明细行添加“已投递”“不感兴趣”按钮；事件写入 `localStorage` 后重新渲染。默认区只渲染 pending；页面底部渲染两个默认隐藏的 `<details>` 区域，显示数量、公司汇总和“撤销”按钮。
- [ ] 重跑 Node 测试，预期 PASS；提交 `feat: collapse marked job listings`。

### Task 3: 全量验证与发布

**Files:** `site/assets/app.js`, `site/index.html`, `site/assets/style.css`

- [ ] 运行 `python -m pytest -q`、`python -m ruff check src tests scripts`、`node tests/test_site.mjs`，预期全部通过。
- [ ] 提交、推送 `main`；Pages 部署后访问网站确认页面包含已投递和不感兴趣区。
