from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx

from autumn_jobs.adapters.cscec8 import crawl_cscec8_jobs, load_cscec8_settings
from autumn_jobs.adapters.guopinleida import crawl_guopinleida_jobs, load_guopinleida_settings
from autumn_jobs.pipeline import run_pipeline
from autumn_jobs.sources import (
    SourceHealth,
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
    try:
        cscec8_jobs = crawl_cscec8_jobs(load_cscec8_settings(Path("config/cscec8.yaml")))
        source_jobs["cscec8"] = cscec8_jobs
        health.append(SourceHealth(source_id="cscec8", status="ok", discovered=len(cscec8_jobs)))
    except (httpx.HTTPError, TypeError) as error:
        health.append(
            SourceHealth(
                source_id="cscec8",
                status="failed",
                discovered=0,
                error=error.__class__.__name__,
            )
        )
    try:
        guopinleida_jobs = crawl_guopinleida_jobs(load_guopinleida_settings(Path("config/guopinleida.yaml")))
        source_jobs["guopinleida"] = guopinleida_jobs
        health.append(SourceHealth(source_id="guopinleida", status="ok", discovered=len(guopinleida_jobs)))
    except (httpx.HTTPError, TypeError) as error:
        health.append(SourceHealth(source_id="guopinleida", status="failed", discovered=0, error=error.__class__.__name__))
    for job in load_verified_jobs(Path("config/verified_jobs.yaml")):
        source_jobs.setdefault(job.source_id, []).append(job)
    today = datetime.now(ZoneInfo("Asia/Shanghai")).date()
    source_status = update_source_status(
        Path("data/state/source_status.json"), health, datetime.now(ZoneInfo("Asia/Shanghai"))
    )
    successful_source_ids = {
        source_id for source_id, row in source_status.items() if row["status"] == "ok"
    }
    result = run_pipeline(
        source_jobs,
        successful_source_ids,
        Path("data/state"),
        Path("site"),
        today,
    )
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(health_payload(health), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"publish_required": result.publish_required, "jobs": result.jobs_count, "health": health_payload(health)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
