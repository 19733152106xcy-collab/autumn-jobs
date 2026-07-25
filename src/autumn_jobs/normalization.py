from __future__ import annotations

import hashlib
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

TRACKING_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "from", "channel", "source"}


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip())


def normalize_company(value: str) -> str:
    value = _clean(value)
    value = re.sub(r"(股份)?有限公司$", "", value)
    return value


def normalize_title(value: str) -> str:
    value = _clean(value)
    return re.sub(r"[（(](20\d{2}届|校招|社招)[）)]", "", value).strip()


def normalize_locations(values: list[str]) -> list[str]:
    cleaned = {_clean(value).replace("市", "") for value in values if _clean(value)}
    return sorted(cleaned) or ["未公布"]


def normalize_url(value: str) -> str:
    parts = urlsplit(value)
    query = [(key, val) for key, val in parse_qsl(parts.query, keep_blank_values=True) if key.lower() not in TRACKING_PARAMS]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), ""))


def make_fingerprint(company: str, title: str, locations: list[str]) -> str:
    base = "\x1f".join((normalize_company(company), normalize_title(title), "|".join(normalize_locations(locations))))
    return hashlib.sha256(base.encode("utf-8")).hexdigest()
