from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from urllib.parse import urljoin

import httpx
import yaml
from selectolax.parser import HTMLParser

from autumn_jobs.models import RawJob

BASE_URL = "https://job.cscec8b.com.cn"
DIRECTORY_URL = f"{BASE_URL}/cscec8b/data/names.json"


def load_cscec8_settings(path: Path) -> dict[str, int]:
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    return {"max_companies": int(config.get("max_companies", 100))}


def _text(node) -> str:
    return " ".join(node.text(separator=" ", strip=True).split()) if node else ""


def parse_cscec8_job(detail_url: str, detail_html: str, description_html: str) -> RawJob:
    tree = HTMLParser(detail_html)
    title = _text(tree.css_first(".job-title-row .title"))
    company_and_date = _text(tree.css_first(".com-or-brc-name"))
    company = re.sub(r"\s*更新：.*$", "", company_and_date).strip()
    date_match = re.search(r"更新：\s*(\d{4}-\d{2}-\d{2})", company_and_date)
    requirements = [
        _text(node) for node in tree.css(".require li") if _text(node) and _text(node) != "|"
    ]
    locations = [part.strip() for part in requirements[0].split("，")] if requirements else ["未公布"]
    source_job_id = detail_url.rstrip("/").rsplit("/", maxsplit=1)[-1]
    description = " ".join(
        [*requirements, _text(HTMLParser(description_html).root)]
    ).strip()
    return RawJob(
        source_id="cscec8",
        source_job_id=source_job_id,
        company=company,
        title=title,
        location=locations,
        detail_url=detail_url,
        apply_url=detail_url,
        publish_date=date.fromisoformat(date_match.group(1)) if date_match else None,
        description=description,
    )


def _published_date(value: object) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _official_status(row: dict[str, object]) -> str:
    status = str(row.get("status", row.get("job_status", ""))).strip().lower()
    return "closed" if status in {"closed", "offline", "ended", "inactive", "0"} else "open"


def _raw_cscec8_job(row: dict[str, object]) -> RawJob:
    job_id = str(row["job_id"])
    detail_url = f"{BASE_URL}/recruitment/job/detail/id/{job_id}"
    description = " ".join(
        str(row.get(field, ""))
        for field in ("job_desc", "ws_g_diploma_name", "job_requirement")
        if row.get(field)
    )
    location = str(row.get("job_address_name", "")).strip()
    return RawJob(
        source_id="cscec8",
        source_job_id=job_id,
        company=str(row.get("ws_company_orgnize_id_user_name", "中建八局")).strip(),
        title=str(row.get("job_name_show", "")).strip(),
        location=[location] if location else ["未公布"],
        detail_url=detail_url,
        apply_url=detail_url,
        publish_date=_published_date(row.get("show_time")),
        description=description,
        official_status=_official_status(row),
    )


def discover_cscec8_jobs(client: httpx.Client, max_companies: int) -> list[RawJob]:
    directory = client.get(DIRECTORY_URL)
    directory.raise_for_status()
    directory_payload = directory.json()
    if not isinstance(directory_payload, dict) or not isinstance(directory_payload.get("list"), list):
        raise TypeError("InvalidDirectoryPayload")

    jobs: list[RawJob] = []
    seen_ids: set[str] = set()
    for company in directory_payload["list"][:max_companies]:
        if not isinstance(company, dict) or not company.get("jobApi"):
            continue
        response = client.get(urljoin(BASE_URL, str(company["jobApi"])))
        response.raise_for_status()
        payload = response.json()
        rows = payload.get("data", {}).get("list") if isinstance(payload, dict) else None
        if not isinstance(rows, list):
            raise TypeError("InvalidJobListPayload")
        for row in rows:
            if not isinstance(row, dict) or not row.get("job_id") or not row.get("job_name_show"):
                continue
            job = _raw_cscec8_job(row)
            if job.source_job_id in seen_ids:
                continue
            seen_ids.add(job.source_job_id or "")
            jobs.append(job)
    return jobs


def crawl_cscec8_jobs(settings: dict[str, int]) -> list[RawJob]:
    jobs: list[RawJob] = []
    headers = {"User-Agent": "autumn-jobs-index/0.1 (+public source monitor)"}
    with httpx.Client(headers=headers, follow_redirects=True, timeout=20.0) as client:
        jobs = discover_cscec8_jobs(client, settings["max_companies"])
    return jobs
