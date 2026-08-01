from __future__ import annotations

import re
from pathlib import Path

import yaml

from autumn_jobs.models import MatchResult, StructuredRequirements

ELIGIBLE_MAJOR_PATTERNS = ("建筑学", "建筑类", "建筑相关", "工程类", "专业不限")
GENERIC_CAMPAIGN_PATTERNS = ("招聘", "校招", "秋招", "人才计划", "招募", "提前批")
GENERIC_CROSS_DIRECTIONS = (
    "AI应用",
    "AI产品",
    "产品与项目",
    "产品方向",
    "项目方向",
    "设计方向",
    "数字化",
    "智慧城市",
    "解决方案",
    "管培生",
)
TRAINING_ROLE_PATTERNS = (
    "教学管培",
    "教师管培",
    "课程顾问",
    "学科教师",
    "主讲教师",
    "教学方向",
    "学科校长",
    "运营校长",
    "教学岗",
)
POSTGRADUATE_ONLY_PATTERNS = (
    r"硕士及以上",
    r"硕士以上",
    r"博士及以上",
    r"博士以上",
    r"研究生及以上",
    r"研究生以上",
    r"仅限(?:硕士|博士|研究生)",
    r"仅招(?:硕士|博士|研究生)",
    r"(?:学历|学位)[：:]?\s*(?:硕士|博士|研究生)",
    r"(?:硕士|博士|研究生).{0,6}(?:学历|学位)",
    r"(?:硕士研究生|博士研究生)",
    r"全日制研究生",
    r"博士专项",
    r"博士后",
)


def _keywords() -> dict[str, list[str]]:
    path = Path(__file__).parents[2] / "config" / "keywords.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _contains(value: str, words: list[str]) -> list[str]:
    lowered = value.lower()
    return [word for word in words if word.lower() in lowered]


def _has_eligible_major(text: str) -> bool:
    return any(pattern in text for pattern in ELIGIBLE_MAJOR_PATTERNS)


def _requires_postgraduate(text: str) -> bool:
    postgraduate_preferred = bool(
        re.search(r"(?:硕士|博士|研究生).{0,6}优先|优先.{0,6}(?:硕士|博士|研究生)", text)
    )
    if postgraduate_preferred:
        return False
    return any(re.search(pattern, text) for pattern in POSTGRADUATE_ONLY_PATTERNS)


def _requirements(text: str) -> StructuredRequirements:
    year = 2027 if "2027" in text else None
    return StructuredRequirements(
        education="本科" if "本科" in text else None,
        graduation_year=year,
        majors=["建筑"] if "建筑" in text else [],
        experience_required=bool(re.search(r"(工作经验|年以上经验).{0,8}(要求|必须)|要求.{0,8}(工作经验|年以上经验)", text)),
        qualification_required="注册建筑师" in text and "优先" not in text,
    )


def classify_opportunity(title: str, description: str) -> str:
    text = f"{title} {description}"
    if "实习" not in text:
        return "full_time"
    if any(marker in text for marker in ("校园招聘", "校招", "秋招", "应届生")):
        return "mixed"
    return "internship"


def match_job(title: str, description: str) -> MatchResult:
    text = f"{title} {description}"
    rules = _keywords()
    requirements = _requirements(text)
    historical_title = any(year in title for year in ("2025", "2026"))
    wrong_year = (
        historical_title or any(year in text for year in ("2025届", "2026届", "已毕业"))
    ) and "2027" not in text
    social_recruitment = any(marker in text for marker in ("社会招聘", "社招")) and not (
        "2027" in text and any(marker in text for marker in ("校园招聘", "校招"))
    )
    if (
        _requires_postgraduate(text)
        or wrong_year
        or social_recruitment
        or requirements.experience_required
        or requirements.qualification_required
    ):
        return MatchResult(included=False, reasons=["明确硬性条件不匹配"], requirements=requirements)
    if _contains(title, rules["title_only_exclude"]):
        return MatchResult(included=False, reasons=["明确不匹配专项技术岗"], requirements=requirements)
    if _contains(title, rules["irrelevant"]):
        return MatchResult(included=False, reasons=["明确无关岗位"], requirements=requirements)
    if any(pattern in text for pattern in TRAINING_ROLE_PATTERNS):
        return MatchResult(included=False, reasons=["教育培训岗位与目标方向无关"], requirements=requirements)
    direct = _contains(title, rules["direct"])
    if not direct and any(marker in title for marker in ("招聘", "校招", "秋招")):
        direct = _contains(description, rules["direct"])
    if direct:
        return MatchResult(
            included=True, level="A", category=direct[0], job_group="architecture", reasons=direct,
            requirements=requirements,
        )
    related = _contains(title, rules["related"])
    if related and _has_eligible_major(description):
        return MatchResult(
            included=True, level="B", category=related[0], job_group="architecture", reasons=related,
            requirements=requirements,
        )
    cross = _contains(title, rules["cross_industry"])
    generic_campaign = any(pattern in title for pattern in GENERIC_CAMPAIGN_PATTERNS)
    body_cross = _contains(description, rules["cross_industry"])
    if (
        not cross
        and generic_campaign
        and body_cross
        and "专业不限" in description
        and any(direction in description for direction in GENERIC_CROSS_DIRECTIONS)
    ):
        cross = body_cross
    relevance = _contains(text, rules["cross_relevance"])
    if cross and relevance:
        return MatchResult(
            included=True, level="C", category=cross[0], job_group="other", reasons=cross + relevance[:1],
            requirements=requirements,
        )
    return MatchResult(included=False, reasons=["未达到C类最低相关性"], requirements=requirements)
