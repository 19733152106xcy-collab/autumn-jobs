from __future__ import annotations

import re
from pathlib import Path

import yaml

from autumn_jobs.models import MatchResult, StructuredRequirements


def _keywords() -> dict[str, list[str]]:
    path = Path(__file__).parents[2] / "config" / "keywords.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _contains(value: str, words: list[str]) -> list[str]:
    lowered = value.lower()
    return [word for word in words if word.lower() in lowered]


def _requirements(text: str) -> StructuredRequirements:
    year = 2027 if "2027" in text else None
    return StructuredRequirements(
        education="本科" if "本科" in text else None,
        graduation_year=year,
        majors=["建筑"] if "建筑" in text else [],
        experience_required=bool(re.search(r"(工作经验|年以上经验).{0,8}(要求|必须)|要求.{0,8}(工作经验|年以上经验)", text)),
        qualification_required="注册建筑师" in text and "优先" not in text,
    )


def match_job(title: str, description: str) -> MatchResult:
    text = f"{title} {description}"
    rules = _keywords()
    requirements = _requirements(text)
    postgraduate_preferred = bool(
        re.search(r"(?:硕士|博士|研究生).{0,6}优先|优先.{0,6}(?:硕士|博士|研究生)", text)
    )
    hard_postgraduate = ("博士" in text or "硕士" in text or "研究生" in text) and any(
        token in text for token in ("必须", "仅限", "仅招", "硕士及以上", "博士及以上")
    ) and not postgraduate_preferred
    degree_field_requires_postgraduate = bool(
        re.search(r"(?:学历|学位).{0,6}(?:硕士|博士|研究生)|(?:硕士|博士|研究生).{0,6}(?:学历|学位)", text)
    ) and not postgraduate_preferred
    wrong_year = any(year in text for year in ("2025届", "2026届", "已毕业")) and "2027" not in text
    social_recruitment = any(marker in text for marker in ("社会招聘", "社招")) and not (
        "2027" in text and any(marker in text for marker in ("校园招聘", "校招"))
    )
    doctoral_only = any(marker in text for marker in ("博士专项", "博士后", "博士研究生"))
    if (
        hard_postgraduate
        or degree_field_requires_postgraduate
        or doctoral_only
        or wrong_year
        or social_recruitment
        or requirements.experience_required
        or requirements.qualification_required
    ):
        return MatchResult(included=False, reasons=["明确硬性条件不匹配"], requirements=requirements)
    if _contains(text, rules["irrelevant"]):
        return MatchResult(included=False, reasons=["明确无关岗位"], requirements=requirements)
    direct = _contains(text, rules["direct"])
    if direct:
        return MatchResult(included=True, level="A", category=direct[0], reasons=direct, requirements=requirements)
    related = _contains(text, rules["related"])
    if related:
        return MatchResult(included=True, level="B", category=related[0], reasons=related, requirements=requirements)
    cross = _contains(text, rules["cross_industry"])
    relevance = _contains(text, rules["cross_relevance"])
    if cross and relevance:
        return MatchResult(included=True, level="C", category=cross[0], reasons=cross + relevance[:1], requirements=requirements)
    return MatchResult(included=False, reasons=["未达到C类最低相关性"], requirements=requirements)
