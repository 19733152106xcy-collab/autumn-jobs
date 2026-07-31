# 建筑岗位精筛与公司状态 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 排除用户专业不能投及硕士硬性要求的岗位，并让用户一次隐藏或恢复整家公司的岗位。

**Architecture:** Python 匹配器采用“标题决定岗位方向、正文只校验投递资格”的顺序，显式专项排除优先于所有包含规则。前端新增独立的公司状态映射，以标准化公司名为键保存在浏览器本地；渲染时先应用公司状态，再应用单岗位状态。

**Tech Stack:** Python 3.12、Pydantic、PyYAML、pytest、原生 JavaScript ES modules、Node assert、GitHub Pages、GitHub Actions。

---

## 文件结构

- 修改 `config/keywords.yaml`：维护标题硬排除词和岗位方向关键词。
- 修改 `src/autumn_jobs/matching.py`：实现标题优先、专业资格校验和硕士硬要求识别。
- 修改 `tests/test_matching.py`：覆盖景观、土木、工程类、硕士要求和公告正文污染。
- 修改 `site/assets/app.js`：实现公司状态存储、分组隐藏、恢复和按钮事件。
- 修改 `site/index.html`：增加“不感兴趣公司”折叠区域。
- 修改 `site/assets/style.css`：复用并补齐公司级按钮与隐藏公司区域样式。
- 修改 `tests/test_site.mjs`：覆盖公司级状态的设置、分区、未来岗位隐藏和撤销。
- 更新 `data/state/jobs.json`、`site/data/jobs.json`、`site/data/update_status.json` 和来源健康摘要：重新运行抓取与筛选后生成。

### Task 1: 收紧岗位匹配规则

**Files:**
- Modify: `tests/test_matching.py`
- Modify: `config/keywords.yaml`
- Modify: `src/autumn_jobs/matching.py`

- [ ] **Step 1: 写失败测试**

在 `tests/test_matching.py` 添加：

```python
import pytest


@pytest.mark.parametrize("title", ["景观设计师", "园林设计岗", "风景园林岗", "土木工程师", "结构设计师", "道路工程师", "桥梁工程师"])
def test_excludes_non_architecture_specialties_even_when_architecture_is_mentioned(title):
    assert match_job(title, "2027届本科，建筑学及相关专业可投").included is False


def test_related_role_requires_an_eligible_major_signal():
    assert match_job("项目管理岗", "2027届本科，土木类专业").included is False
    assert match_job("项目管理岗", "2027届本科，工程类专业").included is True


def test_description_from_other_roles_does_not_change_current_job_direction():
    assert match_job("营销专员", "同时招聘建筑设计、项目管理岗位").included is False


def test_excludes_postgraduate_only_but_keeps_postgraduate_preferred():
    assert match_job("建筑设计岗", "硕士及以上学历，建筑学专业").included is False
    assert match_job("建筑设计岗", "本科及以上，硕士优先，建筑学专业").included is True
```

- [ ] **Step 2: 运行测试并确认按预期失败**

运行：

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_matching.py -v
```

预期：新增的景观、土木和正文污染用例失败；失败原因是现有匹配器仍会使用整篇正文确定岗位方向。

- [ ] **Step 3: 最小实现严格规则**

在 `config/keywords.yaml` 中从 `direct` 删除 `景观设计`，并把以下词加入 `title_only_exclude`：

```yaml
  - 景观
  - 园林
  - 风景园林
  - 土木
  - 岩土
  - 桥梁
```

在 `matching.py` 中：

```python
ELIGIBLE_MAJOR_PATTERNS = ("建筑学", "建筑类", "建筑相关", "工程类", "专业不限")
POSTGRADUATE_ONLY_PATTERNS = (
    r"硕士及以上",
    r"博士及以上",
    r"仅限(?:硕士|博士|研究生)",
    r"仅招(?:硕士|博士|研究生)",
    r"(?:学历|学位)[：:]?\s*(?:硕士|博士|研究生)",
    r"(?:硕士研究生|博士研究生)",
)


def _has_eligible_major(text: str) -> bool:
    return any(pattern in text for pattern in ELIGIBLE_MAJOR_PATTERNS)


def _requires_postgraduate(text: str) -> bool:
    undergraduate_allowed = bool(re.search(r"本科(?:及以上|或以上|可投)", text))
    preferred_only = "优先" in text and undergraduate_allowed
    return not preferred_only and any(re.search(pattern, text) for pattern in POSTGRADUATE_ONLY_PATTERNS)
```

匹配顺序改为：硬性学历排除 → 标题专项排除 → 标题直接岗位 → 标题相关岗位且 `_has_eligible_major(description)` → 标题跨行业岗位且达到最低相关性 → 排除。硕士识别须覆盖“硕士及以上”“硕士研究生”“学历/学位：硕士”“仅限硕士/博士”，并明确豁免“硕士优先”且允许本科的表达。

- [ ] **Step 4: 运行匹配测试**

运行：

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_matching.py -v
```

预期：全部通过。

- [ ] **Step 5: 提交匹配改动**

```powershell
git add tests/test_matching.py config/keywords.yaml src/autumn_jobs/matching.py
git commit -m "fix: restrict jobs to eligible architecture roles"
```

### Task 2: 增加公司级不感兴趣状态

**Files:**
- Modify: `tests/test_site.mjs`
- Modify: `site/assets/app.js`
- Modify: `site/index.html`
- Modify: `site/assets/style.css`

- [ ] **Step 1: 写失败测试**

在 `tests/test_site.mjs` 导入并测试期望接口：

```javascript
const companyStatuses = setCompanyStatus({}, "甲设计院", "not_interested");
assert.deepEqual(companyStatuses, { "甲设计院": "not_interested" });

const companyPartition = partitionJobsByCompanyStatus([
  { fingerprint: "job-1", company: "甲设计院" },
  { fingerprint: "job-2", company: "甲设计院" },
  { fingerprint: "job-3", company: "乙科技" },
], companyStatuses);
assert.deepEqual(companyPartition.pending.map((job) => job.fingerprint), ["job-3"]);
assert.deepEqual(companyPartition.not_interested.map((job) => job.fingerprint), ["job-1", "job-2"]);
assert.deepEqual(setCompanyStatus(companyStatuses, "甲设计院", null), {});
```

- [ ] **Step 2: 运行前端测试并确认按预期失败**

运行：

```powershell
node tests/test_site.mjs
```

预期：因 `setCompanyStatus` 或 `partitionJobsByCompanyStatus` 尚未导出而失败。

- [ ] **Step 3: 实现纯函数和本地存储**

在 `site/assets/app.js` 新增：

```javascript
export function setCompanyStatus(statuses, company, status) {
  const next = { ...statuses };
  if (status) next[company] = status;
  else delete next[company];
  return next;
}

export function partitionJobsByCompanyStatus(jobs, statuses) {
  const groups = { pending: [], not_interested: [] };
  jobs.forEach((job) => groups[statuses[job.company] || "pending"].push(job));
  return groups;
}
```

使用独立键 `autumn-jobs-company-statuses` 读写公司状态。渲染顺序为公司状态分区 → 单岗位状态分区 → 搜索筛选。公司汇总行增加 `mark-company` 按钮；点击保存状态并重绘。

- [ ] **Step 4: 增加恢复区域和事件**

在 `site/index.html` 的保存状态区域增加：

```html
<details id="not-interested-companies-section"><summary>不感兴趣公司（0）</summary><div id="not-interested-companies-list"></div></details>
```

列表只显示公司名、岗位数和“撤销”按钮。撤销时删除该公司状态并重绘；新抓到的同名公司岗位自然继续受状态映射约束。

- [ ] **Step 5: 运行前端测试**

运行：

```powershell
node tests/test_site.mjs
```

预期：退出码 0。

- [ ] **Step 6: 提交公司状态改动**

```powershell
git add tests/test_site.mjs site/assets/app.js site/index.html site/assets/style.css
git commit -m "feat: hide all jobs from ignored companies"
```

### Task 3: 全量回归与重新生成数据

**Files:**
- Modify: `data/state/jobs.json`
- Modify: `data/state/source_status.json`
- Modify: `site/data/jobs.json`
- Modify: `site/data/update_status.json`
- Modify: `artifacts/source-health.json`

- [ ] **Step 1: 运行完整本地测试和静态检查**

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
node tests/test_site.mjs
```

预期：pytest 零失败、ruff 零错误、Node 退出码 0。

- [ ] **Step 2: 全量抓取并应用新筛选规则**

```powershell
.\.venv\Scripts\python.exe scripts/crawl.py --all
```

预期：输出 JSON 摘要；成功来源重新生成岗位，失败来源按安全合并保留，但标题明确命中景观、园林、土木等硬排除项的岗位不得出现在公开数据中。

- [ ] **Step 3: 检查公开数据**

运行以下只读统计，断言公开岗位标题不命中硬排除词，并输出岗位总数、公司数和优先级分布：

```powershell
@'
import json
from collections import Counter
from pathlib import Path

payload = json.loads(Path("site/data/jobs.json").read_text(encoding="utf-8"))
jobs = payload["jobs"]
excluded = ("景观", "园林", "风景园林", "土木", "结构", "水暖", "暖通", "给排水", "机电", "电气", "道路", "桥梁", "隧道")
bad = [(job["company"], job["title"]) for job in jobs if any(word in job["title"] for word in excluded)]
assert not bad, bad[:20]
print({
    "jobs": len(jobs),
    "companies": len({job["company"] for job in jobs}),
    "priority": Counter(job["priority_label"] for job in jobs),
})
'@ | .\.venv\Scripts\python.exe -
```

- [ ] **Step 4: 再次运行完整验证**

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
node tests/test_site.mjs
git diff --check
```

预期：全部退出码 0。

- [ ] **Step 5: 提交数据刷新**

```powershell
git add data/state site/data artifacts/source-health.json
git commit -m "data: refresh eligible 2027 graduate jobs"
```

### Task 4: 推送并验证 GitHub Pages

**Files:**
- No code changes expected.

- [ ] **Step 1: 推送默认分支**

```powershell
git push origin main
```

预期：远端 `main` 更新到本地最新提交。

- [ ] **Step 2: 检查 Actions**

```powershell
D:\tools\GitHubCLI\bin\gh.exe run list --limit 5
```

预期：测试与 Pages 部署工作流成功。

- [ ] **Step 3: 核验线上文件**

读取 `https://19733152106xcy-collab.github.io/autumn-jobs/data/jobs.json`，确认岗位统计与本地一致，并确认线上 `assets/app.js` 含公司级状态功能。
