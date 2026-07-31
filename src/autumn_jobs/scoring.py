from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field

from autumn_jobs.models import MatchResult, RawJob


class ScoreResult(BaseModel):
    eligibility_status: Literal["eligible", "needs_confirmation"]
    eligibility_label: str
    score_total: int
    score_breakdown: dict[str, int]
    salary_band: str
    salary_basis: Literal["明确", "估算", "待确认"]
    score_confidence: Literal["高", "中", "低"]
    score_summary: str
    score_strengths: list[str] = Field(default_factory=list)
    score_risks: list[str] = Field(default_factory=list)


@lru_cache(maxsize=1)
def _settings() -> dict[str, object]:
    path = Path(__file__).parents[2] / "config" / "scoring.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _company_profile(company: str) -> tuple[int, str, str, bool]:
    settings = _settings()
    for profile in settings["company_profiles"]:
        if any(keyword.lower() in company.lower() for keyword in profile["keywords"]):
            return (
                int(profile["platform_points"]),
                str(profile["salary_band"]),
                str(profile["rationale"]),
                True,
            )
    default = settings["default_company"]
    return (
        int(default["platform_points"]),
        str(default["salary_band"]),
        str(default["rationale"]),
        False,
    )


def _monthly_salary(text: str) -> float | None:
    compact = text.replace(",", "")
    k_match = re.search(
        r"(\d{1,2}(?:\.\d+)?)\s*[kK]\s*[-—~至]\s*(\d{1,2}(?:\.\d+)?)\s*[kK]",
        compact,
    )
    if k_match:
        return (float(k_match.group(1)) + float(k_match.group(2))) * 500
    yuan_match = re.search(r"(\d{4,5})\s*[-—~至]\s*(\d{4,5})\s*元", compact)
    if yuan_match:
        return (float(yuan_match.group(1)) + float(yuan_match.group(2))) / 2
    return None


def _salary_score(monthly: float) -> tuple[int, str]:
    if monthly >= 15_000:
        return 38, "A"
    if monthly >= 10_000:
        return 32, "B"
    if monthly >= 5_000:
        return 26, "C"
    return 20, "C"


def _eligibility(raw: RawJob, matched: MatchResult) -> tuple[str, str]:
    description = raw.description
    signals = (
        matched.requirements.education == "本科" or "本科" in description,
        matched.requirements.graduation_year == 2027 or "2027" in description,
        bool(matched.requirements.majors)
        or any(marker in description for marker in ("专业不限", "建筑类", "建筑学", "工程类")),
    )
    if sum(signals) >= 2:
        return "eligible", "可投"
    return "needs_confirmation", "需确认"


def score_job(raw: RawJob, matched: MatchResult) -> ScoreResult:
    weights = {key: int(value) for key, value in _settings()["weights"].items()}
    pure_internship = "实习" in raw.title and not any(
        marker in raw.title for marker in ("校招", "校园招聘", "秋招", "转正")
    )
    eligibility_status, eligibility_label = _eligibility(raw, matched)
    platform_points, estimated_band, company_reason, company_known = _company_profile(raw.company)
    monthly_salary = _monthly_salary(raw.description)
    if monthly_salary is not None:
        compensation_platform, salary_band = _salary_score(monthly_salary)
        salary_basis = "明确"
    else:
        compensation_platform = platform_points
        salary_band = estimated_band
        salary_basis = "估算" if company_known else "待确认"

    interview_probability = {"A": 20, "B": 16, "C": 12}.get(matched.level, 8)
    interview_probability += 2 if eligibility_status == "eligible" else -3
    if raw.verification_status in {"official", "verified"}:
        interview_probability += 2
    if raw.source_type == "official":
        interview_probability += 1
    if pure_internship:
        interview_probability -= 4
    interview_probability = max(0, min(25, interview_probability))

    if matched.job_group == "architecture":
        ability_match = 20 if matched.level == "A" else 16
    elif any(marker in raw.title for marker in ("AI", "人工智能", "数字", "智慧城市", "解决方案")):
        ability_match = 15
    else:
        ability_match = 11

    growth = 10 if compensation_platform >= 35 else 8 if compensation_platform >= 29 else 6
    if any(marker in raw.title for marker in ("AI", "数字化", "智慧城市")):
        growth = min(10, growth + 1)
    if pure_internship:
        growth = max(0, growth - 1)

    if raw.official_apply_url:
        application_cost = 5
    elif raw.apply_url:
        application_cost = 4
    else:
        application_cost = 3
    if raw.verification_status == "pending":
        application_cost = min(application_cost, 2)
    if pure_internship:
        summary = "实习机会，优先确认转正和正式批安排"
    elif eligibility_status == "needs_confirmation":
        application_cost = max(0, application_cost - 1)

    raw_breakdown = {
        "compensation_platform": (min(40, compensation_platform), 40),
        "interview_probability": (interview_probability, 25),
        "ability_match": (min(20, ability_match), 20),
        "growth": (min(10, growth), 10),
        "application_cost": (min(5, application_cost), 5),
    }
    breakdown = {
        key: round(points / maximum * weights[key])
        for key, (points, maximum) in raw_breakdown.items()
    }
    score_total = sum(breakdown.values())

    strengths: list[str] = []
    if salary_basis == "明确":
        strengths.append("招聘信息明确薪资")
    elif company_known:
        strengths.append(company_reason)
    if matched.job_group == "architecture" and matched.level == "A":
        strengths.append("专业与设计院实习经历直接匹配")
    elif ability_match >= 15:
        strengths.append("建筑与AI复合背景可发挥")
    if raw.verification_status in {"official", "verified"}:
        strengths.append("招聘来源已核验")

    risks: list[str] = []
    if eligibility_status == "needs_confirmation":
        risks.append("学历、届别或专业信息不完整")
    if salary_basis == "估算":
        risks.append("待遇为公司层级估算")
    elif salary_basis == "待确认":
        risks.append("公司与待遇信息不足")
    if raw.verification_status == "pending":
        risks.append("投递信息仍待核验")
    if raw.opportunity_type == "internship" or "实习" in raw.title:
        risks.append("实习岗位，需确认转正机会")

    if salary_basis == "明确" and eligibility_status == "eligible" and raw.verification_status != "pending":
        confidence = "高"
    elif company_known or raw.verification_status != "pending":
        confidence = "中"
    else:
        confidence = "低"

    if eligibility_status == "needs_confirmation":
        summary = "信息尚不完整，先核验资格与待遇再投递"
    elif score_total >= 80:
        summary = "待遇平台与匹配度较好，建议优先投递"
    elif score_total >= 65:
        summary = "综合条件尚可，值得安排投递"
    else:
        summary = "可作为补充机会，先核验关键信息"

    return ScoreResult(
        eligibility_status=eligibility_status,
        eligibility_label=eligibility_label,
        score_total=score_total,
        score_breakdown=breakdown,
        salary_band=salary_band,
        salary_basis=salary_basis,
        score_confidence=confidence,
        score_summary=summary,
        score_strengths=strengths[:3],
        score_risks=risks[:3],
    )
