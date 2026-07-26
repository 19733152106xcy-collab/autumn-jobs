"""Low-frequency public source discovery without login state or stored HTML."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
import yaml
from selectolax.parser import HTMLParser

from autumn_jobs.models import RawJob

ANCHOR_TERMS = ("招聘", "校招", "岗位", "建筑", "设计", "bim", "ai", "更新", "规划", "管培")
RECRUITMENT_URL_MARKERS = ("recruit", "job", "zhaopin", "xyzp", "campus")
HISTORICAL_COHORT = re.compile(r"20(?:1\d|2[0-6])届")
GENERIC_RECRUITMENT_TITLES = {"招聘岗位", "校园招聘", "社会招聘"}
ROLE_SUFFIXES = "设计师|工程师|专员|助理|顾问|管培生|管理培训生|实习生"
ROLE_TITLE = re.compile(rf"[\u4e00-\u9fffA-Za-z0-9·（）() -]{{2,40}}(?:{ROLE_SUFFIXES})")
ROLE_ROW = re.compile(r"(?P<prefix>.{2,80}?)\s+(?P<education>博士|硕士|研究生|本科|大专|不限)\s+(?:若干|\d+)")


@dataclass
class SourceHealth:
    source_id: str
    status: str
    discovered: int
    error: str | None = None


def _is_current_recruitment_candidate(text: str, url: str) -> bool:
    """Avoid treating service/project showcase navigation as a job listing."""
    combined = f"{text} {url}"
    if HISTORICAL_COHORT.search(combined) and "2027届" not in combined:
        return False
    path = urlparse(url).path.lower()
    return any(marker in text.lower() for marker in ANCHOR_TERMS) and any(
        marker in path for marker in RECRUITMENT_URL_MARKERS
    )


def extract_role_rows(text: str) -> list[tuple[str, str]]:
    """Extract concrete titles from a simple public recruitment table."""
    if "岗位名称" not in text or "学历" not in text or "详情" not in text:
        return []
    table = text.split("详情", maxsplit=1)[1]
    rows: list[tuple[str, str]] = []
    seen: set[str] = set()
    for match in ROLE_ROW.finditer(table):
        titles = ROLE_TITLE.findall(match.group("prefix"))
        if not titles:
            continue
        title = titles[-1].rsplit("申请该职位", maxsplit=1)[-1].strip()
        if title in seen:
            continue
        seen.add(title)
        rows.append((title, f"学历：{match.group('education')}"))
    return rows


def extract_job_links(base_url: str, html: str, limit: int) -> list[tuple[str, str]]:
    tree = HTMLParser(html)
    links: list[tuple[str, str]] = []
    seen: set[str] = set()
    for anchor in tree.css("a"):
        text = " ".join(anchor.text(separator=" ", strip=True).split())
        href = anchor.attributes.get("href", "")
        if not text or not href or href.startswith(("javascript:", "mailto:", "#")):
            continue
        if not any(term in text.lower() for term in ANCHOR_TERMS):
            continue
        absolute = urljoin(base_url, href)
        if not _is_current_recruitment_candidate(text, absolute):
            continue
        if absolute in seen:
            continue
        seen.add(absolute)
        links.append((text[:160], absolute))
        if len(links) >= limit:
            break
    return links


def _page_text(client: httpx.Client, url: str) -> str:
    response = client.get(url)
    response.raise_for_status()
    return HTMLParser(response.text).text(separator=" ", strip=True)[:30_000]


def crawl_configured_sources(config_path: Path) -> tuple[dict[str, list[RawJob]], list[SourceHealth]]:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    jobs: dict[str, list[RawJob]] = defaultdict(list)
    health: list[SourceHealth] = []
    timeout = httpx.Timeout(connect=10.0, read=20.0, write=10.0, pool=10.0)
    headers = {"User-Agent": "autumn-jobs-index/0.1 (+public source monitor)"}
    with httpx.Client(headers=headers, timeout=timeout, follow_redirects=True) as client:
        for source in config["sources"]:
            if not source.get("enabled", True):
                continue
            source_id = source["id"]
            try:
                root = client.get(source["url"])
                root.raise_for_status()
                links = extract_job_links(str(root.url), root.text, int(source.get("max_items", 10)))
                for title, detail_url in links:
                    try:
                        description = _page_text(client, detail_url)
                    except httpx.HTTPError:
                        description = title
                    role_rows = extract_role_rows(description)
                    if role_rows:
                        for role_title, role_description in role_rows:
                            jobs[source_id].append(
                                RawJob(
                                    source_id=source_id,
                                    company=source["company"],
                                    title=role_title,
                                    location=["未公布"],
                                    detail_url=detail_url,
                                    description=f"{title} {role_description}",
                                )
                            )
                    elif title not in GENERIC_RECRUITMENT_TITLES:
                        jobs[source_id].append(
                            RawJob(
                                source_id=source_id,
                                company=source["company"],
                                title=title,
                                location=["未公布"],
                                detail_url=detail_url,
                                description=description,
                            )
                        )
                health.append(SourceHealth(source_id=source_id, status="ok", discovered=len(links)))
            except httpx.HTTPError as error:
                health.append(SourceHealth(source_id=source_id, status="failed", discovered=0, error=error.__class__.__name__))
    return dict(jobs), health


def load_verified_jobs(config_path: Path) -> list[RawJob]:
    """Load small, manually verified official entries for dynamic-only portals."""
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    return [RawJob.model_validate(row) for row in config.get("jobs", [])]


def health_payload(rows: list[SourceHealth]) -> list[dict[str, object]]:
    return [asdict(row) for row in rows]


def update_source_status(
    path: Path, rows: list[SourceHealth], observed_at: datetime
) -> dict[str, dict[str, object]]:
    """Persist only source health metadata, never page content or credentials."""
    previous: dict[str, dict[str, object]] = {}
    if path.exists():
        previous = json.loads(path.read_text(encoding="utf-8"))
    timestamp = observed_at.isoformat()
    updated: dict[str, dict[str, object]] = {}
    for row in rows:
        old = previous.get(row.source_id, {})
        discovery_drop = row.status == "ok" and int(old.get("discovered", 0)) >= 5 and row.discovered == 0
        succeeded = row.status == "ok" and not discovery_drop
        status = "suspect" if discovery_drop else row.status
        error = "DiscoveryDropToZero" if discovery_drop else row.error
        updated[row.source_id] = {
            "status": status,
            "discovered": row.discovered,
            "last_run": timestamp,
            "last_success": timestamp if succeeded else old.get("last_success"),
            "consecutive_failures": 0 if succeeded else int(old.get("consecutive_failures", 0)) + 1,
            "last_error": None if succeeded else error,
        }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(updated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return updated
