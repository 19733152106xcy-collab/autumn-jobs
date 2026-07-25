"""Read-only technical audit for configured public recruitment sources."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urljoin
from urllib.robotparser import RobotFileParser

import httpx
import yaml


@dataclass(frozen=True)
class AuditRow:
    source_id: str
    final_url: str
    checked_at: str
    access: str
    page_type: str
    public_list: bool
    public_detail: bool
    requires_login_to_apply: bool
    robots_checked: bool
    sample_job_count: int = 0
    error_code: str | None = None
    note: str = ""


def load_audit(path: Path) -> list[AuditRow]:
    return [AuditRow(**row) for row in json.loads(path.read_text(encoding="utf-8"))]


def _robots_checked(url: str) -> bool:
    robots = RobotFileParser(urljoin(url, "/robots.txt"))
    try:
        robots.read()
    except OSError:
        return False
    return robots.can_fetch("autumn-jobs-index", url)


def _classify(response: httpx.Response) -> tuple[str, str, bool, bool, bool, str]:
    content_type = response.headers.get("content-type", "").lower()
    text = response.text[:120_000].lower()
    is_json = "json" in content_type
    is_html = "html" in content_type or "<!doctype" in text or "<html" in text
    requires_login = any(marker in text for marker in ("登录", "注册", "sign in", "login"))
    public_list = response.status_code == 200 and (is_json or is_html)
    public_detail = public_list and not requires_login
    if is_json:
        page_type = "json"
    elif is_html and ("__next" in text or "webpack" in text or "javascript" in text):
        page_type = "dynamic"
    elif is_html:
        page_type = "html"
    else:
        page_type = "unknown"
    if response.status_code == 200:
        access = "partial" if requires_login else "public"
    elif response.status_code in {401, 403, 429}:
        access = "partial"
    else:
        access = "blocked"
    note = f"HTTP {response.status_code}; {content_type or 'unknown content type'}"
    return access, page_type, public_list, public_detail, requires_login, note


def audit_candidates(candidates_path: Path) -> list[AuditRow]:
    payload = yaml.safe_load(candidates_path.read_text(encoding="utf-8"))
    rows: list[AuditRow] = []
    headers = {"User-Agent": "autumn-jobs-index/0.1 (public-source-audit)"}
    timeout = httpx.Timeout(connect=10.0, read=20.0, write=10.0, pool=10.0)
    with httpx.Client(headers=headers, timeout=timeout, follow_redirects=True) as client:
        for candidate in payload["candidates"]:
            checked_at = datetime.now(UTC).isoformat()
            url = candidate["url"]
            try:
                response = client.get(url)
                access, page_type, public_list, public_detail, requires_login, note = _classify(response)
                rows.append(
                    AuditRow(
                        source_id=candidate["id"],
                        final_url=str(response.url),
                        checked_at=checked_at,
                        access=access,
                        page_type=page_type,
                        public_list=public_list,
                        public_detail=public_detail,
                        requires_login_to_apply=requires_login,
                        robots_checked=_robots_checked(str(response.url)),
                        error_code=None if response.status_code == 200 else f"http_{response.status_code}",
                        note=note,
                    )
                )
            except httpx.HTTPError as error:
                rows.append(
                    AuditRow(
                        source_id=candidate["id"],
                        final_url=url,
                        checked_at=checked_at,
                        access="blocked",
                        page_type="unknown",
                        public_list=False,
                        public_detail=False,
                        requires_login_to_apply=False,
                        robots_checked=False,
                        error_code=error.__class__.__name__.lower(),
                        note="request failed without retaining response content",
                    )
                )
    return rows


def write_audit(rows: list[AuditRow], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps([asdict(row) for row in rows], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
