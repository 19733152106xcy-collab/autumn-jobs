# 2027届秋招岗位库 Phase One Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 以 5 个异构真实来源先打通抓取、筛选、去重、安全合并、公开数据生成、极简网页和 GitHub Pages 发布，再在同一实施周期扩展至约 10 个高价值来源。

**Architecture:** Python 包负责来源抓取、结构化、规则匹配、去重、链接检查和状态合并；岗位业务状态与每次运行状态严格分离。`site/` 是唯一发布目录，前端使用原生 HTML/CSS/JavaScript 读取公开 JSON。HTTP 优先，只有动态站点才使用 Playwright。

**Tech Stack:** Python 3.12+、HTTPX、Selectolax、Pydantic、PyYAML、Tenacity、RapidFuzz、Playwright（按需）、pytest、respx、Ruff、GitHub Actions、GitHub Pages。

---

## 文件职责

```text
config/profile.yaml                 匿名求职规则
config/keywords.yaml                A/B/C关键词、硬排除和C类最低相关性
config/sources.yaml                 已审核来源及抓取器映射
src/autumn_jobs/models.py           业务模型、运行模型、公开模型
src/autumn_jobs/privacy.py          日志脱敏和禁止字段校验
src/autumn_jobs/normalization.py    公司、岗位、地点、URL标准化
src/autumn_jobs/matching.py         硬排除、A/B/C匹配与理由
src/autumn_jobs/deduplication.py    指纹、碰撞保护和来源优先级合并
src/autumn_jobs/fetchers.py         HTTP与Playwright抓取边界
src/autumn_jobs/parsers.py          JSON映射和HTML选择器解析
src/autumn_jobs/link_checking.py    valid/suspect/inactive判定
src/autumn_jobs/state.py            业务状态、运行状态和原子写入
src/autumn_jobs/pipeline.py         单次运行编排和发布判断
src/autumn_jobs/sources/*.py        只有通用配置无法表达时才增加站点适配器
scripts/audit_sources.py            来源技术审核
scripts/crawl.py                    本地和Actions统一入口
scripts/build_public_data.py        生成site/data/jobs.json
site/index.html                     极简页面结构
site/assets/app.js                  搜索、筛选、排序和链接回退
site/assets/style.css               桌面表格和手机卡片
tests/fixtures/                     固定JSON/HTML样本，不保存完整无关正文
.github/workflows/ci.yml            测试和静态检查
.github/workflows/daily-update.yml  每日抓取与条件发布
```

## Task 1：审核 10 个候选来源并锁定 5 个垂直切片来源

**Files:**
- Create: `docs/source-audit.md`
- Create: `config/source_candidates.yaml`
- Create: `scripts/audit_sources.py`
- Test: `tests/test_source_audit.py`

- [ ] **Step 1：写入候选来源清单**

候选清单固定从以下 10 个入口开始，审核时允许因官方跳转更新 URL，但必须保留发现链路：

```yaml
candidates:
  - {id: cadg, name: 中国建筑设计研究院, url: "https://hr.cadg.com.cn/", group: official_hr}
  - {id: biad, name: 北京市建筑设计研究院, url: "https://www.biad.com.cn/view/id/233/", group: design_firm}
  - {id: brdr, name: 北京市住宅建筑设计研究院, url: "https://www.brdr.com.cn/html/renliziyuan/zhiyeshengya/index.html", group: design_firm}
  - {id: ccdc, name: 中国中建设计研究院, url: "https://ccdc.cscec.com/rlzy/xyzp/", group: central_soe}
  - {id: cscec, name: 中国建筑校园招聘, url: "https://recruit.cscec.com/recruit/#/portal_job_list?job_class=campus", group: official_hr}
  - {id: xauat, name: 西安建筑科技大学就业信息网, url: "https://job.xauat.edu.cn/", group: university}
  - {id: tongji, name: 同济大学学生就业信息网, url: "https://tj91.tongji.edu.cn/", group: university}
  - {id: seu, name: 东南大学就业信息网, url: "https://job.seu.edu.cn/", group: university}
  - {id: ncss24365, name: 国家24365大学生就业服务平台, url: "https://www.24365.ncss.cn/", group: aggregator}
  - {id: zju, name: 浙江大学就业服务平台, url: "https://www.career.zju.edu.cn/", group: university}
```

- [ ] **Step 2：先写审核结果校验测试**

```python
def test_audit_requires_evidence_for_every_candidate():
    rows = load_audit(Path("docs/source-audit.json"))
    assert len(rows) == 10
    assert all(row.final_url and row.checked_at for row in rows)
    assert all(row.access in {"public", "partial", "blocked"} for row in rows)
    assert all(row.robots_checked for row in rows)
```

- [ ] **Step 3：运行测试并确认失败**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_source_audit.py -v`

Expected: FAIL，因为审核模型和结果文件尚不存在。

- [ ] **Step 4：实现只读审核脚本**

脚本对每个来源记录：最终 URL、状态码、内容类型、是否需要 JavaScript、是否存在公开列表、详情页是否公开、是否需要登录、robots 检查结果、一次抓取岗位数、错误类型和技术建议。不得保存 Cookie、请求头或完整 HTML。

```python
class AuditRow(BaseModel):
    source_id: str
    final_url: HttpUrl
    checked_at: datetime
    access: Literal["public", "partial", "blocked"]
    page_type: Literal["json", "html", "dynamic", "unknown"]
    public_list: bool
    public_detail: bool
    requires_login_to_apply: bool
    robots_checked: bool
    sample_job_count: int = 0
    error_code: str | None = None
```

- [ ] **Step 5：执行真实审核并人工核对 10 条记录**

Run: `.\.venv\Scripts\python.exe scripts\audit_sources.py --input config\source_candidates.yaml --output docs\source-audit.json`

Expected: 10 条记录；任何 blocked 来源保留在报告中但不进入首批 5 个来源。

- [ ] **Step 6：按固定规则选择首批 5 个来源**

选择顺序：`cadg → brdr`、`cscec → ccdc`、`xauat → zju`、`ncss24365 → tongji`、`biad → seu`。每个箭头右侧是左侧不可公开抓取时的替补。最终组合至少包含一个 JSON/API、一个静态 HTML、一个动态页面、一个央国企来源和一个高校来源；若 10 个候选无法满足，停止并向用户展示审核证据，不为凑数接入无关来源。

- [ ] **Step 7：提交来源审核**

```powershell
git add config/source_candidates.yaml docs/source-audit.* scripts/audit_sources.py tests/test_source_audit.py
git commit -m "docs: audit initial recruitment sources"
```

## Task 2：建立可复现的 Python 项目与匿名配置

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `README.md`
- Create: `src/autumn_jobs/__init__.py`
- Create: `config/profile.yaml`
- Create: `config/keywords.yaml`
- Test: `tests/test_package.py`

- [ ] **Step 1：写包导入失败测试**

```python
def test_package_exposes_version():
    import autumn_jobs
    assert autumn_jobs.__version__ == "0.1.0"
```

- [ ] **Step 2：运行测试并确认失败**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_package.py -v`

Expected: FAIL with `ModuleNotFoundError`。

- [ ] **Step 3：创建项目元数据并声明依赖**

`pyproject.toml` 使用 `src` 布局，运行依赖为 `httpx`、`selectolax`、`pydantic`、`PyYAML`、`tenacity`、`rapidfuzz`、`python-dateutil`；动态依赖为 `playwright`；开发依赖为 `pytest`、`pytest-cov`、`respx`、`ruff`。Python 范围固定为 `>=3.12,<3.15`。

- [ ] **Step 4：写匿名画像配置**

```yaml
graduation_year: 2027
education: bachelor
major_groups: [architecture, historic_building_conservation]
allow_cross_industry: true
```

配置不得出现姓名、学校、联系方式或简历路径。

- [ ] **Step 5：写关键词配置并安装可编辑包**

配置包含 A/B/C 标题词、描述词、硬性排除短语、软性“优先”短语、C 类最低相关性词和无关岗位词。执行：

Run: `.\.venv\Scripts\python.exe -m pip install -e ".[dynamic,dev]"`

Expected: 安装成功，包从 `src/autumn_jobs` 导入。

- [ ] **Step 6：运行基础质量门**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_package.py -v`

Expected: PASS。

Run: `.\.venv\Scripts\ruff.exe check .`

Expected: `All checks passed!`

- [ ] **Step 7：提交项目骨架**

```powershell
git add pyproject.toml .gitignore README.md src config tests/test_package.py
git commit -m "build: bootstrap autumn jobs package"
```

## Task 3：定义业务数据、运行状态和隐私边界

**Files:**
- Create: `src/autumn_jobs/models.py`
- Create: `src/autumn_jobs/privacy.py`
- Test: `tests/test_models.py`
- Test: `tests/test_privacy.py`

- [ ] **Step 1：写业务/运行分离测试**

```python
def test_runtime_observation_does_not_change_business_hash(job, observation):
    first = business_hash(job)
    observation.last_seen = observation.last_seen + timedelta(days=1)
    observation.link_last_checked = observation.link_last_checked + timedelta(days=1)
    assert business_hash(job) == first
```

- [ ] **Step 2：写公开数据禁止字段测试**

```python
def test_public_job_has_no_private_or_raw_fields():
    forbidden = {"description", "raw_html", "cookie", "token", "request_headers", "last_seen"}
    assert forbidden.isdisjoint(PublicJob.model_fields)
```

- [ ] **Step 3：运行测试并确认失败**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_models.py tests/test_privacy.py -v`

Expected: FAIL，因为模型尚未定义。

- [ ] **Step 4：实现模型**

```python
class JobBusiness(BaseModel):
    fingerprint: str
    source_id: str
    source_job_id: str | None = None
    company: str
    title: str
    location: list[str]
    deadline: date | None = None
    publish_date: date | None = None
    first_seen: date
    category: str
    match_level: Literal["A", "B", "C"]
    match_reasons: list[str]
    requirements: StructuredRequirements
    apply_url: HttpUrl | None = None
    detail_url: HttpUrl
    alternate_sources: list[HttpUrl] = Field(default_factory=list)
    status: Literal["active", "inactive"] = "active"

class JobObservation(BaseModel):
    fingerprint: str
    source_id: str
    last_seen: datetime | None = None
    link_last_checked: datetime | None = None
    link_state: Literal["unknown", "valid", "suspect"] = "unknown"
    missing_count: int = 0

class PublicJob(BaseModel):
    fingerprint: str
    company: str
    title: str
    location: list[str]
    deadline: date | None
    publish_date: date | None
    first_seen: date
    category: str
    match_level: Literal["A", "B", "C"]
    apply_url: HttpUrl | None
    detail_url: HttpUrl
    status: Literal["active", "inactive"]
```

- [ ] **Step 5：实现脱敏**

`redact_text()` 替换 URL 中的 `token`、`access_token`、`cookie`、`session` 查询值，日志结构拒绝 `headers` 和 `cookies` 字段。

- [ ] **Step 6：运行测试并提交**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_models.py tests/test_privacy.py -v`

Expected: PASS。

```powershell
git add src/autumn_jobs/models.py src/autumn_jobs/privacy.py tests/test_models.py tests/test_privacy.py
git commit -m "feat: separate job business and runtime state"
```

## Task 4：实现标准化、指纹和保守去重

**Files:**
- Create: `src/autumn_jobs/normalization.py`
- Create: `src/autumn_jobs/deduplication.py`
- Create: `config/company_aliases.yaml`
- Test: `tests/test_normalization.py`
- Test: `tests/test_deduplication.py`

- [ ] **Step 1：写跟踪参数和公司别名测试**

```python
def test_normalize_url_drops_tracking_but_keeps_job_id():
    value = normalize_url("https://jobs.example.cn/detail?id=123&utm_source=x&channel=y")
    assert value == "https://jobs.example.cn/detail?id=123"

def test_company_aliases_collapse_known_names():
    assert normalize_company("中国建筑设计研究院有限公司") == "中国建筑设计研究院"
```

- [ ] **Step 2：写同名不同部门不误合并测试**

```python
def test_same_title_different_official_ids_are_not_merged(job_factory):
    a = job_factory(source_job_id="A1", title="建筑设计师")
    b = job_factory(source_job_id="B2", title="建筑设计师")
    assert len(deduplicate([a, b])) == 2
```

- [ ] **Step 3：运行测试并确认失败**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_normalization.py tests/test_deduplication.py -v`

Expected: FAIL。

- [ ] **Step 4：实现标准化和指纹**

指纹基础串固定为 `company\x1ftitle\x1flocation1|location2`，使用 SHA-256。地点排序、去重；标题只移除招聘批次噪声，不移除部门；URL 仅删除配置明确列出的追踪参数。

- [ ] **Step 5：实现碰撞保护和官方链接优先级**

当官方岗位 ID 不同或部门不同，不合并；没有岗位 ID 时，只有基础指纹相同且结构化要求相似度达到 90 才合并。合并时官方投递页优先，并把其他详情地址放入 `alternate_sources`。

- [ ] **Step 6：运行测试并提交**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_normalization.py tests/test_deduplication.py -v`

Expected: PASS。

```powershell
git add src/autumn_jobs/normalization.py src/autumn_jobs/deduplication.py config/company_aliases.yaml tests/test_normalization.py tests/test_deduplication.py
git commit -m "feat: normalize and deduplicate job records"
```

## Task 5：实现高召回但有边界的规则匹配

**Files:**
- Create: `src/autumn_jobs/matching.py`
- Test: `tests/test_matching.py`

- [ ] **Step 1：写硬排除与“优先”区分测试**

```python
@pytest.mark.parametrize("text", ["硕士及以上学历，必须取得硕士学位", "仅限博士研究生"])
def test_required_postgraduate_is_excluded(text):
    assert match_job("建筑设计", text).included is False

def test_postgraduate_preferred_is_not_excluded():
    result = match_job("建筑设计", "本科及以上，硕士优先")
    assert result.included is True
    assert result.level == "A"
```

- [ ] **Step 2：写 C 类最低相关性测试**

```python
def test_unknown_sales_role_is_not_kept_as_c():
    assert match_job("电话销售", "负责客户开拓").included is False

def test_ai_solution_role_can_be_c():
    result = match_job("AI解决方案助理", "本科应届生，专业不限")
    assert result.included is True
    assert result.level == "C"
```

- [ ] **Step 3：运行测试并确认失败**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_matching.py -v`

Expected: FAIL。

- [ ] **Step 4：实现确定性匹配顺序**

匹配顺序固定为：解析硬条件 → 检查届别和学历 → A 标题/描述命中 → B 命中 → C 最低相关性 → 无关岗位排除。结果必须带 `match_reasons`；排除结果只进入 Actions 计数，不写入公开数据。

- [ ] **Step 5：运行测试并提交**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_matching.py -v`

Expected: PASS。

```powershell
git add src/autumn_jobs/matching.py config/keywords.yaml tests/test_matching.py
git commit -m "feat: classify eligible jobs with bounded recall"
```

## Task 6：实现通用 HTTP、JSON 和 HTML 抓取边界

**Files:**
- Create: `src/autumn_jobs/fetchers.py`
- Create: `src/autumn_jobs/parsers.py`
- Test: `tests/test_fetchers.py`
- Test: `tests/test_parsers.py`
- Create: `tests/fixtures/sample_jobs.json`
- Create: `tests/fixtures/sample_jobs.html`

- [ ] **Step 1：写 HTTP 重试边界测试**

```python
@respx.mock
def test_fetch_retries_503_but_not_404():
    route = respx.get("https://example.cn/jobs").mock(side_effect=[Response(503), Response(200, text="ok")])
    assert HttpFetcher().get_text("https://example.cn/jobs") == "ok"
    assert route.call_count == 2
```

- [ ] **Step 2：写配置解析测试**

```python
def test_html_parser_maps_list_and_detail_fields():
    records = HtmlParser(spec).parse(load_fixture("sample_jobs.html"))
    assert records[0].company == "某设计院"
    assert records[0].detail_url.endswith("/jobs/123")
```

- [ ] **Step 3：运行测试并确认失败**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_fetchers.py tests/test_parsers.py -v`

Expected: FAIL。

- [ ] **Step 4：实现抓取器**

HTTPX 客户端使用 10 秒连接、20 秒读取超时，最多 2 次临时错误重试，遵守来源级最小请求间隔。404/410 不重试；403/429 最多一次退避后转为结构化错误。响应正文设置大小上限。

- [ ] **Step 5：实现通用解析器**

JSON 解析器支持点路径字段映射；HTML 解析器支持 CSS 选择器、属性和相对 URL 合并。解析器只返回原始岗位候选，不负责匹配或状态合并。

- [ ] **Step 6：运行测试并提交**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_fetchers.py tests/test_parsers.py -v`

Expected: PASS。

```powershell
git add src/autumn_jobs/fetchers.py src/autumn_jobs/parsers.py tests/test_fetchers.py tests/test_parsers.py tests/fixtures
git commit -m "feat: add bounded fetchers and generic parsers"
```

## Task 7：实现来源健康、安全合并和无意义提交防护

**Files:**
- Create: `src/autumn_jobs/state.py`
- Test: `tests/test_state.py`

- [ ] **Step 1：写来源归零保护测试**

```python
def test_sudden_zero_keeps_previous_jobs(previous_state):
    run = SourceRun(source_id="cadg", outcome="suspicious_zero", jobs=[])
    merged = merge_run(previous_state, run)
    assert merged.jobs == previous_state.jobs
    assert merged.publish_required is False
```

- [ ] **Step 2：写运行状态不触发发布测试**

```python
def test_only_observation_time_changes_do_not_publish(previous_state):
    run = successful_run_with_same_jobs(previous_state, checked_at=NEXT_DAY)
    merged = merge_run(previous_state, run)
    assert merged.business_changed is False
    assert merged.publish_required is False
```

- [ ] **Step 3：运行测试并确认失败**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_state.py -v`

Expected: FAIL。

- [ ] **Step 4：实现双状态文件和业务哈希**

`data/state/jobs.json` 只保存岗位业务状态；`data/runtime/source_status.json` 保存运行观测。公开数据内容哈希排除检查时间。写文件使用同目录临时文件加 `Path.replace()`，进程异常时不得留下半个 JSON。

- [ ] **Step 5：实现健康阈值**

来源请求失败、解析失败、历史中位数至少 5 且本次少于中位数 30%、或历史非零而本次为零时，本次不能推进缺失计数。连续缺失只产生 review 标记，不直接 inactive。

- [ ] **Step 6：运行测试并提交**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_state.py -v`

Expected: PASS。

```powershell
git add src/autumn_jobs/state.py tests/test_state.py
git commit -m "feat: merge source runs without destructive drops"
```

## Task 8：实现保守链接状态机

**Files:**
- Create: `src/autumn_jobs/link_checking.py`
- Test: `tests/test_link_checking.py`

- [ ] **Step 1：写状态转换参数化测试**

```python
@pytest.mark.parametrize(("signal", "previous", "expected"), [
    ("deadline_passed", "active", "inactive"),
    ("page_closed_text", "active", "inactive"),
    ("http_404", "active", "suspect"),
    ("http_403", "active", "suspect"),
    ("captcha", "active", "suspect"),
    ("homepage_redirect", "active", "suspect"),
])
def test_link_policy(signal, previous, expected):
    assert classify_link(signal, previous).state == expected
```

- [ ] **Step 2：写官方 ID 连续两次不存在测试**

```python
def test_official_id_requires_two_confirmations():
    first = apply_signal(active_job(), "official_id_missing")
    assert first.status == "active"
    second = apply_signal(first, "official_id_missing")
    assert second.status == "inactive"
```

- [ ] **Step 3：运行测试并确认失败**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_link_checking.py -v`

Expected: FAIL。

- [ ] **Step 4：实现状态机并运行测试**

检测优先访问 `detail_url`，`apply_url` 只检查可达性；一次异常不隐藏。页面结束文本采用来源级正则，避免通用“结束”字样误判。

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_link_checking.py -v`

Expected: PASS。

- [ ] **Step 5：提交**

```powershell
git add src/autumn_jobs/link_checking.py tests/test_link_checking.py
git commit -m "feat: add conservative job link state machine"
```

## Task 9：接入首批 5 个真实来源

**Files:**
- Create or Modify: `config/sources.yaml`
- Create as required: `src/autumn_jobs/sources/cadg.py`
- Create as required: `src/autumn_jobs/sources/cscec.py`
- Create as required: `src/autumn_jobs/sources/xauat.py`
- Create as required: `src/autumn_jobs/sources/ncss24365.py`
- Create as required: `src/autumn_jobs/sources/biad.py`
- Test: `tests/sources/test_cadg.py`
- Test: `tests/sources/test_cscec.py`
- Test: `tests/sources/test_xauat.py`
- Test: `tests/sources/test_ncss24365.py`
- Test: `tests/sources/test_biad.py`

- [ ] **Step 1：为审核选中的每个来源保存最小固定样本**

样本只保留一至两个岗位和解析必需字段；移除脚本、追踪参数、Cookie、无关正文和个人数据。若采用替补来源，同步替换对应文件名和 source ID，并在 `docs/source-audit.md` 记录理由。

- [ ] **Step 2：逐个写失败测试**

每个来源至少断言：来源 ID、岗位数大于零、公司/标题/地点/详情链接提取、届别或招聘类型、无原始 HTML 进入模型。动态来源另断言无持久化浏览器 storage state。

- [ ] **Step 3：先用通用配置实现，必要时才写适配器**

`config/sources.yaml` 示例：

```yaml
sources:
  - id: cadg
    enabled: true
    priority: official
    fetcher: html
    url: https://hr.cadg.com.cn/
    rate_limit_seconds: 2
    parser:
      item_selector: ".job-item"
      title_selector: ".job-title"
      detail_link_selector: "a"
```

选择器必须来自 Task 1 的真实审核结果，不能猜测。通用配置无法表达分页、接口签名或动态请求时才增加站点适配器。

- [ ] **Step 4：逐来源运行固定样本测试**

Run: `.\.venv\Scripts\python.exe -m pytest tests/sources -v`

Expected: 5 个来源全部 PASS。

- [ ] **Step 5：运行一次低频真实抓取**

Run: `.\.venv\Scripts\python.exe scripts\crawl.py --sources cadg,cscec,xauat,ncss24365,biad --dry-run --max-pages 2`

Expected: 每个来源输出健康状态；没有来源依赖登录 Cookie；失败来源按审核替补规则更换，不伪造岗位。

- [ ] **Step 6：提交首批来源**

```powershell
git add config/sources.yaml src/autumn_jobs/sources tests/sources tests/fixtures docs/source-audit.md
git commit -m "feat: add five audited recruitment sources"
```

## Task 10：编排完整流水线并生成公开 JSON

**Files:**
- Create: `src/autumn_jobs/pipeline.py`
- Create: `scripts/crawl.py`
- Create: `scripts/build_public_data.py`
- Create: `site/data/jobs.json`
- Create: `site/data/update_status.json`
- Test: `tests/test_pipeline.py`
- Test: `tests/test_public_data.py`

- [ ] **Step 1：写完整链路测试**

```python
def test_pipeline_filters_deduplicates_and_builds_public_json(tmp_path):
    result = run_pipeline(fixture_sources(), state_dir=tmp_path / "state", site_dir=tmp_path / "site")
    assert result.source_count == 5
    assert result.duplicate_count >= 1
    payload = json.loads((tmp_path / "site/data/jobs.json").read_text("utf-8"))
    assert all("description" not in row for row in payload["jobs"])
    assert all(row["apply_url"] or row["detail_url"] for row in payload["jobs"])
```

- [ ] **Step 2：写无业务变化不重写公开文件测试**

```python
def test_identical_business_data_keeps_public_file_mtime(tmp_path):
    first = run_fixture_pipeline(tmp_path)
    mtime = first.public_path.stat().st_mtime_ns
    second = run_fixture_pipeline(tmp_path, checked_at=NEXT_DAY)
    assert second.publish_required is False
    assert second.public_path.stat().st_mtime_ns == mtime
```

- [ ] **Step 3：运行测试并确认失败**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_pipeline.py tests/test_public_data.py -v`

Expected: FAIL。

- [ ] **Step 4：实现编排和条件写入**

流水线顺序固定为 fetch → parse → normalize → match → deduplicate → merge → link policy → validate → conditional write。`update_status.json` 只在发布时写业务更新时间；每次运行详情进入 Actions step summary，不进入网站文件。

- [ ] **Step 5：运行测试并提交**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_pipeline.py tests/test_public_data.py -v`

Expected: PASS。

```powershell
git add src/autumn_jobs/pipeline.py scripts/crawl.py scripts/build_public_data.py site/data tests/test_pipeline.py tests/test_public_data.py
git commit -m "feat: build validated public job data"
```

## Task 11：实现极简响应式岗位页

**Files:**
- Create: `site/index.html`
- Create: `site/assets/app.js`
- Create: `site/assets/style.css`
- Create: `tests/frontend/test_page.mjs`

- [ ] **Step 1：写前端数据函数测试**

```javascript
assert.equal(searchJobs(jobs, "设计院").length, 1);
assert.equal(filterJobs(jobs, { city: "西安", level: "A" }).length, 1);
assert.equal(resolveApplyUrl({ apply_url: null, detail_url: "https://example.cn/detail" }), "https://example.cn/detail");
```

- [ ] **Step 2：运行测试并确认失败**

Run: `node tests/frontend/test_page.mjs`

Expected: FAIL，因为函数尚未实现。

- [ ] **Step 3：实现页面结构和行为**

页面只包含标题、最近更新时间、今日新增/全部岗位、搜索、方向、城市、匹配等级、排序和岗位列表。桌面表格列固定为公司、岗位、工作地点、截止日期、投递；手机端以同字段卡片展示。默认只显示 active，A/B/C 全部显示。

- [ ] **Step 4：实现安全链接与空状态**

投递按钮使用 `target="_blank" rel="noopener noreferrer"`。没有匹配结果时显示“当前筛选下暂无岗位”，数据加载失败时显示上次部署不可用提示，不展示调试栈。

- [ ] **Step 5：运行前端测试和本地视觉检查**

Run: `node tests/frontend/test_page.mjs`

Expected: PASS。

Run: `.\.venv\Scripts\python.exe -m http.server 8000 --directory site`

Check: 桌面宽度 1440px 和手机宽度 390px；搜索、组合筛选、排序、今日新增、链接回退均可用。

- [ ] **Step 6：提交**

```powershell
git add site/index.html site/assets tests/frontend
git commit -m "feat: add practical responsive jobs index"
```

## Task 12：配置 CI、每日更新和官方 Pages 部署

**Files:**
- Create: `.github/workflows/ci.yml`
- Create: `.github/workflows/daily-update.yml`
- Modify: `README.md`
- Test: `tests/test_workflows.py`

- [ ] **Step 1：写 workflow 静态校验测试**

```python
def test_daily_workflow_has_required_permissions():
    workflow = load_yaml(".github/workflows/daily-update.yml")
    assert workflow["permissions"] == {
        "contents": "write", "pages": "write", "id-token": "write"
    }
```

- [ ] **Step 2：写调度和官方 Pages actions 测试**

断言 `30 7 * * *`、`Asia/Shanghai`、`workflow_dispatch`、并发锁、超时，以及 `actions/configure-pages`、`actions/upload-pages-artifact`、`actions/deploy-pages` 均存在。

- [ ] **Step 3：运行测试并确认失败**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_workflows.py -v`

Expected: FAIL。

- [ ] **Step 4：实现工作流**

抓取 job 运行测试、执行 crawl、比较公开业务哈希、仅在业务变化时提交 `data/state/jobs.json` 与 `site/data/*`。无业务变化时只写 `$GITHUB_STEP_SUMMARY`。部署 job 仅在 `publish_required=true` 时上传 `site/` 并发布。

- [ ] **Step 5：补充 60 天停用说明**

README 明确：schedule 只在默认分支运行、可能延迟、公开仓库 60 天无活动可能停用；列出在 Actions 页面手动运行 `workflow_dispatch` 和重新启用工作流的方法。

- [ ] **Step 6：运行全部本地质量门并提交**

Run: `.\.venv\Scripts\ruff.exe check .`

Expected: `All checks passed!`

Run: `.\.venv\Scripts\python.exe -m pytest -v`

Expected: 全部 PASS。

```powershell
git add .github README.md tests/test_workflows.py
git commit -m "ci: automate validated daily updates and pages deploy"
```

## Task 13：完成 5 来源真实演示验收门

**Files:**
- Create: `docs/phase-one-demo.md`
- Create: `artifacts/source-health.json`
- Create: `artifacts/sample-public-jobs.json`

- [ ] **Step 1：执行一次真实完整运行**

Run: `.\.venv\Scripts\python.exe scripts\crawl.py --all --write-state --summary artifacts\source-health.json`

Expected: 5 个来源均有明确健康状态；失败来源不导致历史岗位减少。

- [ ] **Step 2：再次运行验证幂等性**

Run: `.\.venv\Scripts\python.exe scripts\crawl.py --all --write-state --summary artifacts\source-health-second.json`

Expected: 没有业务变化时 `publish_required=false`，公开岗位文件内容哈希不变。

- [ ] **Step 3：验证公开数据**

Run: `.\.venv\Scripts\python.exe -m pytest -v`

Expected: 全部 PASS；公开数据无 description、Cookie、Token、请求头或个人信息；所有展示岗位至少有 `detail_url`。

- [ ] **Step 4：推送到用户 GitHub 仓库并手动运行 Actions**

此步需要用户提供或确认 GitHub 仓库归属。创建远程仓库、推送和开启 Pages 属于外部状态变更，执行前再次确认目标仓库。工作流成功后记录 run URL 和 Pages URL。

- [ ] **Step 5：向用户展示四项证据并暂停扩源**

展示：真实抓到的岗位数据、桌面/手机网页效果、来源健康状态、一次完整 Actions 运行结果。用户确认后才执行 Task 14。

- [ ] **Step 6：提交演示记录**

```powershell
git add docs/phase-one-demo.md artifacts/source-health.json artifacts/sample-public-jobs.json
git commit -m "docs: record five-source vertical slice demo"
```

## Task 14：扩展到约 10 个来源

**Files:**
- Modify: `config/sources.yaml`
- Modify: `docs/source-audit.md`
- Create as selected: `tests/sources/test_brdr.py`
- Create as selected: `tests/sources/test_ccdc.py`
- Create as selected: `tests/sources/test_zju.py`
- Create as selected: `tests/sources/test_tongji.py`
- Create as selected: `tests/sources/test_seu.py`
- Create only when generic parsing is insufficient: `src/autumn_jobs/sources/brdr.py`
- Create only when generic parsing is insufficient: `src/autumn_jobs/sources/ccdc.py`
- Create only when generic parsing is insufficient: `src/autumn_jobs/sources/zju.py`
- Create only when generic parsing is insufficient: `src/autumn_jobs/sources/tongji.py`
- Create only when generic parsing is insufficient: `src/autumn_jobs/sources/seu.py`

- [ ] **Step 1：按配额选择剩余 5 个来源**

最终约 10 个来源的目标配额为：3 个官方招聘系统、2 个设计院或建筑企业官网、2 个央国企招聘平台、2 个高校就业网、1 个补充聚合来源。一个来源可只计入一个配额。

- [ ] **Step 2：对每个新增来源重复固定样本测试、低频真实抓取和健康阈值验证**

默认扩展顺序为 brdr、ccdc、zju、tongji、seu。若其中某个已经作为首批替补使用，则用首批未使用的 cadg、cscec、xauat、ncss24365 或 biad 补位。每次只接入一个来源；测试通过并真实抓到结构化数据后单独提交，避免五个来源同时出错难以定位。

- [ ] **Step 3：连续运行观察**

至少完成三次独立运行，确认没有突然归零误删、重复暴涨或单次错误隐藏岗位。来源不稳定时禁用该来源并保留审核记录。

- [ ] **Step 4：提交每个来源**

例如接入 brdr 时：

```powershell
git add config/sources.yaml docs/source-audit.md src/autumn_jobs/sources/brdr.py tests/sources/test_brdr.py
git commit -m "feat: add audited source brdr"
```

如果 brdr 使用通用解析器，不创建或暂存 `src/autumn_jobs/sources/brdr.py`；其他来源使用同样的一来源一提交规则，并在提交信息中写实际 source ID。

- [ ] **Step 5：完成一期最终验收**

再次展示真实岗位、网页、来源健康和 Actions 运行。满足规格中的约 10 来源、匹配岗位全保留、失败不误删、无意义运行不发布、链接保守失效和隐私要求后，一期结束。
