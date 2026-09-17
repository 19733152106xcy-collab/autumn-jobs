from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path
from urllib.parse import urljoin

import httpx
import yaml
from selectolax.parser import HTMLParser

from autumn_jobs.models import RawJob

BASE_URL = "https://job.hust.edu.cn"
LISTING_URL = f"{BASE_URL}/zpxx123123/index.htm"


def load_hust_settings(path: Path) -> dict[str, object]:
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    return {
        "pages": int(config["pages"]),
        "max_items": int(config["max_items"]),
        "max_workers": int(config.get("max_workers", 5)),
        "title_keywords": [str(value) for value in config.get("title_keywords", [])],
    }


def _listing_url(page: int) -> str:
    return LISTING_URL if page == 1 else f"{BASE_URL}/zpxx123123/index_{page}.htm"


def _text(html: str) -> str:
    tree = HTMLParser(html)
    content = tree.css_first(".content")
    return " ".join((content or tree).text(separator=" ", strip=True).split())


def _company(title: str) -> str:
    company = re.split(r"(?:20\d{2}届|校园招聘|校招|秋招|招聘)", title, maxsplit=1)[0]
    return company.strip(" -—：:|") or title


def _published_date(value: str) -> date | None:
    match = re.search(r"(20\d{2}-\d{2}-\d{2})", value)
    return date.fromisoformat(match.group(1)) if match else None


def crawl_hust_jobs(settings: dict[str, object]) -> list[RawJob]:
    listing_rows: list[tuple[str, str, str | None]] = []
    seen: set[str] = set()
    title_keywords = [str(value).lower() for value in settings.get("title_keywords", [])]
    with httpx.Client(timeout=20.0, follow_redirects=True) as client:
        for page in range(1, int(settings["pages"]) + 1):
            response = client.get(_listing_url(page))
            response.raise_for_status()
            tree = HTMLParser(response.text)
            for item in tree.css("ul.nytzlist li"):
                anchor = item.css_first("a[href*='/zpinfo1/']")
                if anchor is None or not anchor.attributes.get("href"):
                    continue
                detail_url = urljoin(BASE_URL, anchor.attributes["href"])
                source_job_id = detail_url.rsplit("/", maxsplit=1)[-1].removesuffix(".htm")
                if source_job_id in seen:
                    continue
                seen.add(source_job_id)
                title = anchor.text(strip=True)
                if title_keywords and not any(keyword in title.lower() for keyword in title_keywords):
                    continue
                published = item.css_first("time")
                listing_rows.append((
                    title,
                    detail_url,
                    published.text(strip=True) if published else None,
                ))
                if len(listing_rows) >= int(settings["max_items"]):
                    break
            if len(listing_rows) >= int(settings["max_items"]):
                break

    def fetch_detail(row: tuple[str, str, str | None]) -> RawJob:
        title, detail_url, published = row
        response = httpx.get(detail_url, timeout=20.0, follow_redirects=True)
        response.raise_for_status()
        source_job_id = detail_url.rsplit("/", maxsplit=1)[-1].removesuffix(".htm")
        return RawJob(
                    source_id="hust",
                    source_job_id=source_job_id,
                    company=_company(title),
                    title=title,
                    location=["未公布"],
                    detail_url=detail_url,
                    description=_text(response.text),
                    publish_date=_published_date(published or ""),
                    source_type="university",
                    verification_status="verified",
                    source_name="华中科技大学就业信息网",
                )

    with ThreadPoolExecutor(max_workers=int(settings.get("max_workers", 5))) as executor:
        return list(executor.map(fetch_detail, listing_rows))
