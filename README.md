# 2027届秋招岗位库

一个公开来源、规则筛选、静态发布的个人岗位索引页。它只承诺保留已配置来源中成功抓取且匹配的岗位，不承诺覆盖全网。

## 本地运行

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dynamic,dev]"
.\.venv\Scripts\python.exe scripts\audit_sources.py --input config\source_candidates.yaml --output docs\source-audit.json
.\.venv\Scripts\python.exe scripts\crawl.py --all
.\.venv\Scripts\python.exe -m http.server 8000 --directory site
```

打开 `http://localhost:8000` 查看网页。

## 数据与隐私

- 页面只读取 `site/data/jobs.json`；岗位描述、Cookie、Token、请求头和个人资料不会发布。
- `data/state/jobs.json` 仅在岗位业务变化时更新；运行状态不会制造无意义的 Pages 发布。
- 单次 404、403、429、验证码、超时或异常跳转只会成为 `suspect`，不会直接隐藏岗位。

## 自动运行

每日工作流在北京时间 7:30 运行，支持 Actions 页面的 **Run workflow** 手动更新。定时任务只在默认分支执行，GitHub 高负载时可能延迟；公开仓库长时间无活动时应在 Actions 页面检查并重新启用定时工作流。
