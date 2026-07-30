from __future__ import annotations

from datetime import date
from pathlib import Path

import httpx
import yaml

from autumn_jobs.models import RawJob

BASE_URL = "https://guopinleida.com"


def load_guopinleida_settings(path: Path) -> dict[str, int]:
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    return {"max_pages": int(config["max_pages"]), "page_size": int(config["page_size"])}


def _parse_date(value: object) -> date | None:
    if not isinstance(value, str) or len(value) < 10:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def crawl_guopinleida_jobs(settings: dict[str, int]) -> list[RawJob]:
    jobs: list[RawJob] = []
    seen: set[str] = set()
    with httpx.Client(timeout=20.0, follow_redirects=True) as client:
        for page in range(settings["max_pages"]):
            response = client.get(
                f"{BASE_URL}/api/jobs",
                params={"recruitmentYear": "27届", "take": settings["page_size"], "skip": page * settings["page_size"]},
            )
            response.raise_for_status()
            payload = response.json()
            rows = payload.get("data", {}).get("data") if isinstance(payload, dict) else None
            if not isinstance(rows, list):
                raise TypeError("InvalidGuopinLeidaPayload")
            for row in rows:
                if not isinstance(row, dict) or not row.get("id") or not row.get("title"):
                    continue
                job_id = str(row["id"])
                if job_id in seen:
                    continue
                seen.add(job_id)
                company = row.get("company", {}) if isinstance(row.get("company"), dict) else {}
                locations = row.get("locations") if isinstance(row.get("locations"), list) else []
                jobs.append(RawJob(
                    source_id="guopinleida",
                    source_job_id=job_id,
                    company=str(company.get("name") or "国聘雷达发布企业"),
                    title=str(row["title"]),
                    location=[str(value) for value in locations] or ["未公布"],
                    detail_url=str(row.get("detailUrl") or f"{BASE_URL}/jobs/{job_id}"),
                    apply_url=None,
                    description=str(row.get("description") or ""),
                    deadline=_parse_date(row.get("deadline")),
                    publish_date=_parse_date(row.get("publishedAt")),
                    source_type="job_board",
                    verification_status="pending",
                    source_name="国聘雷达",
                ))
            meta = payload.get("data", {}).get("meta", {}) if isinstance(payload, dict) else {}
            if not meta.get("hasMore", False):
                break
    return jobs
