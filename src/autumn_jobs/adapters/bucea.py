from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import httpx
import yaml
from selectolax.parser import HTMLParser

from autumn_jobs.models import RawJob

BASE_URL = "https://job.bucea.edu.cn"
CHANNEL_URL = f"{BASE_URL}/front/channel.jspa?channelId=763&parentId=741"
API_URL = f"{BASE_URL}/front/zp_query/zpxxQuery.do"


def load_bucea_settings(path: Path) -> dict[str, int]:
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    return {"max_pages": int(config["max_pages"])}


def _text(html: str) -> str:
    tree = HTMLParser(html)
    content = tree.css_first(".content")
    return " ".join((content or tree).text(separator=" ", strip=True).split())


def _published_date(value: object):
    if not isinstance(value, int):
        return None
    return datetime.fromtimestamp(value / 1000, tz=UTC).date()


def crawl_bucea_jobs(settings: dict[str, int]) -> list[RawJob]:
    jobs: list[RawJob] = []
    with httpx.Client(timeout=20.0, follow_redirects=True) as client:
        channel = client.get(CHANNEL_URL)
        channel.raise_for_status()
        token = HTMLParser(channel.text).css_first('input[name="rzcxt"]')
        if token is None or not token.attributes.get("value"):
            raise TypeError("MissingBuceaChannelToken")
        for page in range(1, settings["max_pages"] + 1):
            response = client.post(
                API_URL,
                data={"xxlx": "1", "curPage": str(page), "rzcxt": token.attributes["value"]},
                headers={"Referer": CHANNEL_URL},
            )
            response.raise_for_status()
            payload = response.json()
            rows = payload.get("data") if isinstance(payload, dict) else None
            if payload.get("msg") != "Y" or not isinstance(rows, list):
                raise TypeError("InvalidBuceaPayload")
            for notice in rows:
                if not isinstance(notice, dict):
                    continue
                company = str(notice.get("dwmc") or "北京建筑大学就业网发布企业")
                locations = [str(notice.get("dwszddm") or "未公布")]
                notice_id = str(notice.get("tid") or "")
                positions = notice.get("xqzwList") if isinstance(notice.get("xqzwList"), list) else []
                for position in positions:
                    if not isinstance(position, dict) or not position.get("id") or not notice_id:
                        continue
                    position_id = str(position["id"])
                    detail_url = f"{BASE_URL}/front/zwxx.jspa?xqzwId={position_id}&zpxxId={notice_id}"
                    detail = client.get(detail_url)
                    detail.raise_for_status()
                    jobs.append(RawJob(
                        source_id="bucea",
                        source_job_id=f"{notice_id}:{position_id}",
                        company=company,
                        title=str(position.get("xqzw") or company),
                        location=locations,
                        detail_url=detail_url,
                        description=_text(detail.text),
                        publish_date=_published_date(notice.get("updateTime")),
                        source_type="university",
                        verification_status="verified",
                        source_name="北京建筑大学就业网",
                    ))
            if page >= int(payload.get("pageCount", page)):
                break
    return jobs
