"""Run sales discovery alone without replacing existing architecture data."""
import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from autumn_jobs.adapters.guopinleida import crawl_guopinleida_jobs
from autumn_jobs.sales import build_sales
from autumn_jobs.sources import load_verified_jobs

parser = argparse.ArgumentParser()
parser.add_argument("--date")
args = parser.parse_args()
today = datetime.fromisoformat(args.date).date() if args.date else datetime.now(ZoneInfo("Asia/Shanghai")).date()
rows = crawl_guopinleida_jobs({"max_pages": 100, "page_size": 100})
sources = {"guopinleida": rows}
for job in load_verified_jobs(Path("config/sales_verified.yaml")):
    sources.setdefault(job.source_id, []).append(job)
payload = build_sales(sources, Path("config/sales_companies.yaml"), Path("site/data/sales.json"), today)
print(json.dumps({"raw": len(rows), "jobs": len(payload["jobs"]), "leads": len(payload["leads"]), "companies": len(payload["companies"])}, ensure_ascii=False))
