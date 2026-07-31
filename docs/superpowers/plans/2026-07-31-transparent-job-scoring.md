# 透明岗位综合评分 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为每个岗位生成可解释的投递资格和百分制优先级，并在网页上按公司最高分展示与排序。

**Architecture:** 新增独立 Python 评分模块读取 YAML 权重与公司档位，根据原始岗位、匹配结果和用户匿名背景生成结构化评分；流水线只负责调用并发布字段。前端读取评分字段，默认按总分排序并用折叠明细展示依据，旧数据字段缺失时安全降级。

**Tech Stack:** Python、Pydantic、PyYAML、pytest、原生 JavaScript ES modules、Node assert、GitHub Pages。

---

### Task 1: 评分模型与透明规则

**Files:**
- Create: `src/autumn_jobs/scoring.py`
- Create: `config/scoring.yaml`
- Create: `tests/test_scoring.py`
- Modify: `src/autumn_jobs/models.py`
- Modify: `src/autumn_jobs/pipeline.py`
- Modify: `tests/test_pipeline.py`

- [ ] **Step 1: 写评分失败测试**

`tests/test_scoring.py` 覆盖以下行为：

```python
def test_score_is_a_transparent_hundred_point_total():
    result = score_job(official_architecture_job(), architecture_match())
    assert result.score_total == sum(result.score_breakdown.values())
    assert set(result.score_breakdown) == {
        "compensation_platform", "interview_probability", "ability_match",
        "growth", "application_cost",
    }
    assert 0 <= result.score_total <= 100


def test_explicit_salary_takes_precedence_over_company_estimate():
    result = score_job(job(description="月薪15k-20k，2027届本科，建筑学"), architecture_match())
    assert result.salary_band == "A"
    assert result.salary_basis == "明确"


def test_missing_requirements_are_marked_for_confirmation():
    result = score_job(job(description="校园招聘"), architecture_match())
    assert result.eligibility_status == "needs_confirmation"
    assert "学历、届别或专业信息不完整" in result.score_risks
```

- [ ] **Step 2: 运行并确认失败**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_scoring.py -v
```

预期：因 `autumn_jobs.scoring` 不存在而失败。

- [ ] **Step 3: 增加评分配置**

`config/scoring.yaml` 定义固定权重：

```yaml
weights:
  compensation_platform: 40
  interview_probability: 25
  ability_match: 20
  growth: 10
  application_cost: 5
default_company:
  platform_points: 22
  salary_band: 待确认
  rationale: 公司待遇信息不足
company_profiles:
  - keywords: [腾讯, 阿里, 字节, 华为, CVTE, 东软]
    platform_points: 36
    salary_band: A
    rationale: 头部科技平台估算
  - keywords: [中国建筑设计研究院, 中建西南院, 华东建筑设计研究院, 广东省建筑设计研究院, 清华同衡]
    platform_points: 33
    salary_band: B
    rationale: 头部建筑设计平台估算
  - keywords: [中建, 中国联合工程, 电力规划设计研究院]
    platform_points: 29
    salary_band: B
    rationale: 央国企工程平台估算
```

- [ ] **Step 4: 实现评分器与数据模型**

`scoring.py` 暴露 `score_job(raw: RawJob, matched: MatchResult) -> ScoreResult`。实现明确薪资提取、公司配置匹配、资格完整度、五项封顶计分、加分项、风险项和可信度。`models.py` 为 `JobBusiness` 增加带默认值的公开评分字段，确保旧状态 JSON 可加载。

- [ ] **Step 5: 接入流水线并验证公开字段**

在 `_to_business` 调用 `score_job`，把评分结果写入 `JobBusiness`；在 `_public_payload` 白名单加入全部评分字段。`tests/test_pipeline.py` 断言五项之和等于总分、公开数据不含 description、资格状态与解释存在。

- [ ] **Step 6: 运行测试与检查**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_scoring.py tests/test_pipeline.py -q
.\.venv\Scripts\python.exe -m ruff check src/autumn_jobs/scoring.py src/autumn_jobs/models.py src/autumn_jobs/pipeline.py tests/test_scoring.py tests/test_pipeline.py
```

预期：零失败、零错误。

- [ ] **Step 7: 提交后端评分**

```powershell
git add config/scoring.yaml src/autumn_jobs/scoring.py src/autumn_jobs/models.py src/autumn_jobs/pipeline.py tests/test_scoring.py tests/test_pipeline.py
git commit -m "feat: score job opportunities transparently"
```

### Task 2: 综合分排序与评分明细

**Files:**
- Modify: `tests/test_site.mjs`
- Modify: `site/index.html`
- Modify: `site/assets/app.js`
- Modify: `site/assets/style.css`

- [ ] **Step 1: 写前端失败测试**

```javascript
const scored = sortJobs([
  { company: "低分公司", score_total: 55, eligibility_status: "eligible", first_seen: "2026-07-31" },
  { company: "高分公司", score_total: 88, eligibility_status: "eligible", first_seen: "2026-07-30" },
], "综合评分");
assert.deepEqual(scored.map((job) => job.company), ["高分公司", "低分公司"]);
```

- [ ] **Step 2: 运行并确认失败**

```powershell
node tests/test_site.mjs
```

预期：当前排序仍按更新时间，断言失败。

- [ ] **Step 3: 实现排序和安全降级**

`sortJobs` 在“综合评分”模式按 `score_total ?? -1` 降序，同分时 `eligible` 优先，再按 `first_seen`。旧“优先级”分支继续保留以避免兼容性回归。

- [ ] **Step 4: 实现公司行与岗位明细**

公司行显示最高分岗位的分数、资格、待遇档位和该公司 `score_total >= 75 && eligibility_status === "eligible"` 的岗位数量。岗位行增加“评分明细”折叠内容，显示五项分数、可信度、加分项、风险项和估算标记。字段缺失时显示“暂未评分”，不得抛出异常。

- [ ] **Step 5: 更新默认控件与样式**

排序下拉框改为“综合评分/更新时间”；为分数、资格、待遇档位和评分明细增加简洁标签样式，保持移动端横向表格可用。

- [ ] **Step 6: 验证并提交**

```powershell
node tests/test_site.mjs
git diff --check
git add tests/test_site.mjs site/index.html site/assets/app.js site/assets/style.css
git commit -m "feat: explain and sort job scores"
```

预期：Node 退出码 0，diff 无空白错误。

### Task 3: 全量重算、发布与线上核验

**Files:**
- Modify: `data/state/jobs.json`
- Modify: `data/state/source_status.json`
- Modify: `site/data/jobs.json`
- Modify: `site/data/update_status.json`

- [ ] **Step 1: 完整验证**

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
node tests/test_site.mjs
```

预期：全部通过。

- [ ] **Step 2: 全量抓取重算**

```powershell
.\.venv\Scripts\python.exe scripts/crawl.py --all
```

预期：公开数据发生业务变化，所有有效岗位生成评分字段。

- [ ] **Step 3: 校验数据不变量**

读取 `site/data/jobs.json` 并断言：每个岗位 `score_total == sum(score_breakdown.values())`、总分在0至100、字段齐全、公开数据无 description；输出岗位数、公司数、分数区间和资格分布。

- [ ] **Step 4: 再次验证并提交数据**

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
node tests/test_site.mjs
git diff --check
git add data/state site/data
git commit -m "data: publish transparent job scores"
```

- [ ] **Step 5: 合并、推送与部署核验**

合并到 `main` 后推送；确认 CI 和 Deploy Pages 成功。线上 `jobs.json` 的岗位数、评分字段与本地一致，线上 `app.js` 包含“综合评分”和“评分明细”。

