from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from autumn_jobs.pipeline import run_pipeline
from autumn_jobs.sources import (
    crawl_configured_sources,
    health_payload,
    load_verified_jobs,
    update_source_status,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Crawl public job sources and build site data.")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--summary", type=Path, default=Path("artifacts/source-health.json"))
    args = parser.parse_args()
    source_jobs, health = crawl_configured_sources(Path("config/sources.yaml"))
    for job in load_verified_jobs(Path("config/verified_jobs.yaml")):
        source_jobs.setdefault(job.source_id, []).append(job)
    today = datetime.now(ZoneInfo("Asia/Shanghai")).date()
    result = run_pipeline(source_jobs, Path("data/state"), Path("site"), today)
    update_source_status(Path("data/state/source_status.json"), health, datetime.now(ZoneInfo("Asia/Shanghai")))
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(health_payload(health), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"publish_required": result.publish_required, "jobs": result.jobs_count, "health": health_payload(health)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
