from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import httpx
import yaml
from selectolax.parser import HTMLParser

from autumn_jobs.models import RawJob

PUBLIC_URL = "https://www.gankinterview.cn/campus?tab=state"


def load_gankinterview_settings(path: Path) -> dict[str, int]:
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    return {"max_rows": int(config.get("max_rows", 50))}


def _date(value: str) -> date | None:
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _roles(positions: str) -> list[str]:
    role_text = positions.split("、", maxsplit=1)[0]
    roles = [part.strip() for part in re.split(r"[,，;；]", role_text) if part.strip()]
    return roles[:20]


def parse_gankinterview_jobs(html: str, max_rows: int = 50) -> list[RawJob]:
    jobs: list[RawJob] = []
    tree = HTMLParser(html)
    for row in tree.css("tbody tr")[:max_rows]:
        cells = [" ".join(cell.text(separator=" ", strip=True).split()) for cell in row.css("td")]
        if len(cells) < 8:
            continue
        company, ownership, positions, location, recruitment_type, cohorts, updated, deadline = cells[:8]
        if "2027届" not in cohorts or not company or not positions:
            continue
        internship = "实习" in recruitment_type
        for role in _roles(positions):
            jobs.append(
                RawJob(
                    source_id="gankinterview",
                    source_job_id=f"{company}:{updated}:{recruitment_type}:{role}",
                    company=company,
                    title=f"{role}（实习）" if internship else role,
                    location=[part.strip() for part in location.split(",") if part.strip()]
                    or ["未公布"],
                    detail_url=PUBLIC_URL,
                    description=f"{cohorts} {ownership} {recruitment_type} {positions}",
                    deadline=_date(deadline),
                    publish_date=_date(updated),
                    source_type="job_board",
                    verification_status="pending",
                    source_name="Gank Interview 国央企校招汇总",
                    opportunity_type="internship" if internship else "full_time",
                )
            )
    return jobs


def crawl_gankinterview_jobs(settings: dict[str, int]) -> list[RawJob]:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/136 Safari/537.36"
        ),
        "Accept-Language": "zh-CN,zh;q=0.9",
    }
    with httpx.Client(headers=headers, follow_redirects=True, timeout=30.0) as client:
        response = client.get(PUBLIC_URL)
        response.raise_for_status()
        if "/auth/login" in str(response.url):
            raise TypeError("GankInterviewPublicPageUnavailable")
        return parse_gankinterview_jobs(response.text, settings["max_rows"])
