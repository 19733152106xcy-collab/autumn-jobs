# GitHub 复用审计（2026-07-25）

## 结论

不直接复制现成“校招爬虫”仓库。当前相关项目要么没有明确许可证，要么依赖 Cookie、代理或绕过反爬，要么采用与一期冲突的数据库/后台架构。项目只安装成熟、许可证清晰的基础库，并独立验证真实招聘来源。

## 审核过的招聘项目

| 项目 | 许可证 | 结论 | 原因 |
|---|---|---|---|
| [tomxin7/jiandan_job](https://github.com/tomxin7/jiandan_job) | 未声明 | 不复制代码，仅把高校就业网列表作为候选线索 | Python 3.6 时代项目，站点结构可能已变化，无明确代码复用许可 |
| [hunhunzhang/Campus-Jobs-Scraper](https://github.com/hunhunzhang/Campus-Jobs-Scraper) | 未声明 | 不复制代码 | 展示了 Playwright 拦截公开 API 的可行性，但站点集中在互联网公司，且无明确许可证 |
| [ooooyasumi/cn-job-harvester](https://github.com/ooooyasumi/cn-job-harvester) | 未声明 | 不复制代码 | 模块化方向接近，但无明确许可证，且公司范围与本项目不同 |
| [DaqiHu/UnifiedWebCrawler](https://github.com/DaqiHu/UnifiedWebCrawler) | MIT | 不安装 | 连接器思路可借鉴，但包含 Streamlit、SQLite 和原始快照，超出一期范围 |
| [speedyapply/JobSpy](https://github.com/speedyapply/JobSpy) | MIT | 一期不安装 | 适合 LinkedIn/Indeed 等聚合补充源，但官方直投率低、易限流，留到首批官方来源稳定后评估 |
| [ever-jobs/ever-jobs](https://github.com/ever-jobs/ever-jobs) | 需进一步核对 | 不安装 | NestJS 单体规模过大，主要覆盖海外 ATS 和招聘网站，不符合轻量 Python 方案 |

## 采用的基础组件

| 组件 | 用途 | 采用理由 |
|---|---|---|
| [encode/httpx](https://github.com/encode/httpx) | HTTP 客户端 | 严格超时、连接池、重定向控制、同步与异步接口 |
| [rushter/selectolax](https://github.com/rushter/selectolax) | 静态 HTML 解析 | 支持 CSS 选择器，轻量、速度快 |
| [microsoft/playwright-python](https://github.com/microsoft/playwright-python) | 动态页面和公开 API 观察 | 仅在 HTTP 抓取不足时启用，不保存登录态 |
| [pydantic/pydantic](https://github.com/pydantic/pydantic) | 数据模型与公开数据校验 | 防止缺字段或类型错误发布到 Pages |
| [jd/tenacity](https://github.com/jd/tenacity) | 有边界的临时错误重试 | 统一重试 429、5xx 和网络异常，不重试确定业务错误 |
| [rapidfuzz/RapidFuzz](https://github.com/rapidfuzz/RapidFuzz) | 去重碰撞保护 | 辅助区分同名岗位与相似描述 |
| [pytest-dev/pytest](https://github.com/pytest-dev/pytest) 与 [lundberg/respx](https://github.com/lundberg/respx) | 自动测试 | 使用固定网页样本和 HTTP mock 验证失败保护 |
| [astral-sh/ruff](https://github.com/astral-sh/ruff) | 代码检查 | 单一工具完成格式和静态检查 |

PyYAML 用于配置，python-dateutil 用于日期解析。所有 Python 依赖安装在 `D:\projects\autumn-jobs\.venv`；如果后续需要下载 Playwright 专用浏览器，目标位置固定为 `D:\projects\autumn-jobs\.playwright-browsers`。

## 已安装版本

项目专用虚拟环境已安装并验证以下版本：

```text
httpx==0.28.1
selectolax==0.4.11
pydantic==2.13.4
PyYAML==6.0.3
tenacity==9.1.4
python-dateutil==2.9.0.post0
RapidFuzz==3.14.5
playwright==1.61.0
pytest==9.1.1
pytest-cov==7.1.0
respx==0.23.1
ruff==0.16.0
```

Windows 本地 Chromium 下载在网络阶段超时，因此没有把不完整浏览器视为安装成功。本地 Playwright 已使用系统 Chrome 完成无头启动、访问 `https://example.com`、读取标题和正常关闭验证。GitHub Actions 的 Linux runner 在需要动态来源时执行 `python -m playwright install --with-deps chromium`；静态来源不承担浏览器安装成本。

## 禁止做法

- 不关闭或绕过目标站 robots 规则；
- 不把 Cookie、Token、登录态或代理凭据提交进仓库；
- 不复制无许可证仓库代码；
- 不通过频繁请求规避限流；
- 不在一期引入 Scrapy、Streamlit、SQLite、Pandas 或完整招聘聚合框架。
