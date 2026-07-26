# 2027 Formal Autumn Jobs Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 今天收录当前公开可访问、与你匹配的 2027 届正式校园招聘岗位，并把同一套来源变成每天自动增量更新的稳定任务。

**Architecture:** 来源分为官方招聘系统、企业官网、政府/央企平台、高校就业网和补充线索五层。每个来源先解析为统一 `RawJob`，再经过届别与学历硬过滤、A/B/C 匹配、去重、保守链接检查和业务数据发布；JavaScript 招聘系统优先调用公开 JSON 接口，浏览器只用于接口调查和无法静态访问的少数来源。

**Tech Stack:** Python 3.12、httpx、selectolax、Pydantic、PyYAML、Playwright（仅调查动态来源）、GitHub Actions、GitHub Pages。

---

## 收录边界

- 只收 2027 届全职校园招聘、秋招正式批和明确面向 2027 届的提前批全职岗位。
- 暂不把日常实习、暑期实习、留用实习、社会招聘、宣讲会和只有公司介绍的招聘入口显示成岗位。
- A/B/C 全部保留，但 C 类至少命中 AI、数字化、智慧城市、产品、解决方案、项目实施、三维内容、专业不限或管培生之一。
- 招聘活动页只有在能够解析到具体岗位或明确岗位方向时才公开；否则只作为来源线索。
- 单次访问失败不删除旧岗位；只有明确截止、官方下线或连续确认不存在才隐藏。

## 来源覆盖矩阵

### 第一层：直接投递的官方招聘系统

- 中国建筑招聘系统及中建八局独立系统：`recruit.cscec.com`、`job.cscec8b.com.cn`。
- 中建科技、中建设计院、中建各工程局、设计管理院等公开岗位页。
- 建筑央企与工程企业：中铁、铁建、交建、中冶、电建、能建、化学工程等官方校园招聘页。
- 设计院和规划院：中国建筑设计研究院、北京市建筑设计研究院及已审计的企业官网。
- 跨行业正式校招：米哈游、百度、阿里、字节、华为、普渡等官方校园招聘系统。

### 第二层：政府和央国企平台

- 人社部中央企业招聘信息公开平台。
- 国家大学生就业服务平台 / 24365。
- 国聘及中央、地方国资招聘栏目。

这些平台用于发现企业和公告，最终投递链接仍回溯到企业官方系统。

### 第三层：高价值高校就业网

- 西安建筑科技大学、同济、东南、北建大、华南理工、重庆大学、天津大学、浙大等建筑与工程优势院校。
- 南开、山大等更新及时、公开可访问的综合高校就业网。

高校页面用于补充招聘简章、专业要求、宣讲批次和发布日期，不优先作为投递地址。

### 第四层：搜索与聚合线索

- 搜索引擎定向查询官方域名和 `2027届 + 岗位关键词`。
- 应届生、牛客、实习僧等仅作线索，不直接作为最终岗位来源。
- 企业官方公众号文章仅在能回溯到官方详情或投递页时入库。

## Task 1: 建立正式批来源清单和证据状态

**Files:**
- Modify: `config/source_candidates.yaml`
- Modify: `config/sources.yaml`
- Create: `config/formal_batch_sources.yaml`
- Modify: `docs/source-audit.json`
- Test: `tests/test_source_audit.py`

- [ ] **Step 1: 写失败测试，要求正式批来源具备类型、官方性、适配器和验证日期**

```python
def test_formal_batch_sources_have_verification_evidence():
    config = yaml.safe_load(Path("config/formal_batch_sources.yaml").read_text(encoding="utf-8"))
    assert len(config["sources"]) >= 30
    for source in config["sources"]:
        assert source["kind"] in {"official_api", "official_html", "government", "university", "lead"}
        assert source["adapter"]
        assert source["verified_on"]
```

- [ ] **Step 2: 运行测试并确认因清单缺失而失败**

Run: `.\.venv\Scripts\python.exe -m pytest tests\test_source_audit.py -v`

Expected: FAIL，提示 `formal_batch_sources.yaml` 不存在或字段不足。

- [ ] **Step 3: 写入至少 30 个高价值来源，按官方 API、官方 HTML、政府、高校和线索分组**

- [ ] **Step 4: 逐个记录 HTTP 状态、是否需要 JavaScript、是否能得到具体岗位、robots 结果和失败原因**

- [ ] **Step 5: 运行来源审计测试并提交**

```powershell
.\.venv\Scripts\python.exe scripts\audit_sources.py --input config\formal_batch_sources.yaml --output docs\source-audit.json
.\.venv\Scripts\python.exe -m pytest tests\test_source_audit.py -v
git add config docs tests/test_source_audit.py
git commit -m "data: audit 2027 formal recruitment sources"
```

## Task 2: 解析中建八局正式批具体岗位

**Files:**
- Create: `src/autumn_jobs/adapters/cscec8.py`
- Create: `src/autumn_jobs/adapters/__init__.py`
- Modify: `src/autumn_jobs/sources.py`
- Test: `tests/adapters/test_cscec8.py`

- [ ] **Step 1: 保存最小脱敏响应样本，只包含岗位字段，不保存整页 HTML**

- [ ] **Step 2: 写失败测试，覆盖 2027、本科、地点、发布时间和官方岗位 ID**

```python
def test_cscec8_adapter_emits_formal_2027_job(sample_payload):
    jobs = parse_cscec8_jobs(sample_payload)
    assert jobs[0].source_job_id == "2757"
    assert jobs[0].title == "设计管理总院2027届校园招聘"
    assert jobs[0].location == ["上海浦东新区"]
    assert "本科及以上" in jobs[0].description
```

- [ ] **Step 3: 实现公开接口解析器，并把 2026 届、硕士硬要求和社会招聘交给统一规则排除**

- [ ] **Step 4: 用真实接口跑一遍，检查中建科技、设计管理总院、三公司、上海公司、土木公司、浙江公司、发展建设公司和华北管培生等当前 2027 正式批**

- [ ] **Step 5: 运行适配器与全量测试并提交**

```powershell
.\.venv\Scripts\python.exe -m pytest tests\adapters\test_cscec8.py -v
.\.venv\Scripts\python.exe -m pytest -q
git add src/autumn_jobs/adapters src/autumn_jobs/sources.py tests/adapters
git commit -m "feat: crawl cscec8 2027 formal jobs"
```

## Task 3: 接入跨行业正式校招官方系统

**Files:**
- Create: `src/autumn_jobs/adapters/json_api.py`
- Create: `config/dynamic_sources.yaml`
- Modify: `src/autumn_jobs/sources.py`
- Test: `tests/adapters/test_json_api.py`

- [ ] **Step 1: 调查米哈游、百度、阿里、字节、华为、普渡的公开职位接口，记录请求方法、分页和岗位详情 URL 模板**

- [ ] **Step 2: 写失败测试，要求只保留 2027 全职校园招聘，排除实习项目**

```python
def test_dynamic_adapter_excludes_internships():
    jobs = parse_json_jobs(FIXTURE, graduation_year=2027, employment_type="full_time")
    assert jobs
    assert all("实习" not in job.title for job in jobs)
```

- [ ] **Step 3: 实现配置驱动的 JSON 字段映射、分页和详情链接生成**

- [ ] **Step 4: 对产品、解决方案、项目实施、产品运营、三维内容、数字化和专业不限管培岗位应用 C 类最低相关性规则**

- [ ] **Step 5: 运行测试并提交**

## Task 4: 扩展建筑央企、设计院和高校来源

**Files:**
- Create: `src/autumn_jobs/adapters/list_detail.py`
- Modify: `config/formal_batch_sources.yaml`
- Test: `tests/adapters/test_list_detail.py`

- [ ] **Step 1: 写失败测试，要求列表页发现的链接必须进入详情页提取岗位、学历、专业、城市和截止日期**

- [ ] **Step 2: 实现列表—详情适配器，并为 HTML/PDF 招聘简章只保留结构化结果**

- [ ] **Step 3: 接入可公开访问的中铁、铁建、交建、中冶、电建、能建、化学工程、建筑设计院和建筑优势高校来源**

- [ ] **Step 4: 对微信、登录、验证码和小程序来源标记 `blocked`，不伪造零岗位状态**

- [ ] **Step 5: 运行测试并提交**

## Task 5: 今天的正式批数据生成与人工抽查

**Files:**
- Modify: `data/state/jobs.json`
- Modify: `data/state/source_status.json`
- Modify: `site/data/jobs.json`
- Modify: `site/data/update_status.json`
- Create: `artifacts/formal-batch-review.json`（不提交）

- [ ] **Step 1: 运行所有正式批来源**

```powershell
.\.venv\Scripts\python.exe scripts\crawl.py --all --summary artifacts\source-health.json
```

- [ ] **Step 2: 对所有新增岗位检查届别、学历、专业、岗位级别、地点和官方链接**

- [ ] **Step 3: 删除入口页、宣讲会、旧届、实习和没有最低相关性的 C 类噪声**

- [ ] **Step 4: 在本地网页验证搜索、筛选、今日新增和投递链接**

- [ ] **Step 5: 运行全量验证并提交业务数据**

```powershell
.\.venv\Scripts\python.exe -m pytest -q
node tests\frontend\test_page.mjs
.\.venv\Scripts\ruff.exe check .
git diff --check
git add data/state site/data
git commit -m "data: publish current 2027 formal autumn jobs"
```

## Task 6: 每日增量更新和异常保护

**Files:**
- Modify: `.github/workflows/daily-update.yml`
- Modify: `src/autumn_jobs/link_checking.py`
- Modify: `src/autumn_jobs/state.py`
- Test: `tests/test_workflows.py`
- Test: `tests/test_source_status.py`

- [ ] **Step 1: 写失败测试，覆盖来源从历史非零突然变零、单次 404、403、429、超时、验证码和首页跳转**

- [ ] **Step 2: 每天北京时间 7:30 抓取，手动运行保留 `workflow_dispatch`**

- [ ] **Step 3: 只有岗位新增、变化、失效或链接变化才更新网页；来源检查时间只进入健康状态和 Actions 摘要**

- [ ] **Step 4: 上传 30 天来源健康 artifact，连续失败和岗位数骤降在摘要中标红**

- [ ] **Step 5: 运行全量测试并提交**

## Task 7: GitHub 发布和每日运行验收

**Files:**
- Modify: `README.md`
- Verify: `.github/workflows/daily-update.yml`

- [ ] **Step 1: 连接用户授权的 GitHub 仓库并推送 `main`**

- [ ] **Step 2: 将 Pages Source 设置为 GitHub Actions**

- [ ] **Step 3: 手动运行一次 Daily job update，验证抓取、测试、提交和 Pages 部署**

- [ ] **Step 4: 检查网页的真实岗位、来源健康 artifact、Actions 摘要和直接投递链接**

- [ ] **Step 5: 记录公开仓库 60 天无活动可能暂停 schedule 的维护说明**

## 完成标准

- 今天网页展示配置来源内当前抓到、规则匹配并人工抽查通过的 2027 届正式全职岗位。
- 每个公开岗位有企业、具体岗位或明确招聘方向、地点、发布日期/截止日期（若有）、A/B/C、官方详情和投递链接。
- 动态招聘系统使用公开数据接口，不把空 HTML 当成零岗位。
- 新来源只需增加配置或一个小型适配器，不修改主流程。
- 每天自动更新；来源失败不误删旧岗位；网页无业务变化不重复部署。
