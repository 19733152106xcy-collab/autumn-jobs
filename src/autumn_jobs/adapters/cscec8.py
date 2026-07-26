from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import httpx
import yaml
from selectolax.parser import HTMLParser

from autumn_jobs.models import RawJob

BASE_URL = "https://job.cscec8b.com.cn"


def load_cscec8_job_ids(path: Path) -> list[int]:
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    return [int(job_id) for job_id in config.get("job_ids", [])]


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


def crawl_cscec8_jobs(job_ids: list[int]) -> list[RawJob]:
    jobs: list[RawJob] = []
    headers = {"User-Agent": "autumn-jobs-index/0.1 (+public source monitor)"}
    with httpx.Client(headers=headers, follow_redirects=True, timeout=20.0) as client:
        for job_id in job_ids:
            detail_url = f"{BASE_URL}/recruitment/job/detail/id/{job_id}"
            detail = client.get(detail_url)
            detail.raise_for_status()
            description = client.get(f"{BASE_URL}/headhunter/showjobdesc/id/{job_id}")
            description.raise_for_status()
            jobs.append(parse_cscec8_job(detail_url, detail.text, description.text))
    return jobs
