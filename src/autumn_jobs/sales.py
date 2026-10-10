"""Independent, conservative ToB sales discovery. Never reuse architecture exclusions."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date
from pathlib import Path
from urllib.parse import quote

import yaml

from autumn_jobs.models import RawJob

SALES = re.compile(r"销售|客户经理|大客户|商务拓展|商务代表|渠道经理|渠道拓展|营销|客户经营|客户成功|business development|account manager", re.IGNORECASE)
CAMPAIGN = re.compile(r"校园招聘|校招|招聘简章|招聘公告|全球招聘")
ROLE = re.compile(r"销售|客户经理|商务拓展|商务代表|渠道经理|渠道拓展|客户经营|客户成功", re.IGNORECASE)


def role_name(title: str) -> str:
    return re.sub(r"2027|27届|校招|（2027公告列出）|（专业不设限）|[\s-]", "", title)


def expand_campaign(job: RawJob) -> list[RawJob]:
    """Only explicit short role names in lists; never copy campaign eligibility to a role."""
    if not CAMPAIGN.search(job.title) or not re.search(r"2027|27届", job.title):
        return []
    roles = []
    for part in re.split(r"[,，、;；\n\\]", job.description):
        title = re.sub(r"^(?:销售类|市场类|营销类|岗位|招聘职位)[:：]", "", part).strip()
        if 2 <= len(title) <= 24 and ROLE.search(title) and not re.search(
            r"本科|硕士|学历|专业|经验|负责|公司|客户需求|招聘|实习|增长|业务覆盖|门店|导购", title
        ) and not re.search(r"类$|方向$|族$|岗位$|//", title):
            roles.append(job.model_copy(update={
                "title": title + "（2027公告列出）",
                "description": "公告明确列出该销售岗位名称，具体岗位学历、专业、薪酬和工作地点仍需核验。",
                "verification_status": "pending",
            }))
    return roles


def classify_sales(job: RawJob) -> dict | None:
    text = job.title + " " + job.description
    if not SALES.search(text):
        return None
    if job.opportunity_type == "internship" or re.search(r"实习|ByteIntern|internship", job.title, re.IGNORECASE):
        return None
    if re.search(r"(?:硕士|研究生|博士)(?:及以上|以上|学历|学位|起)", text) and not re.search(r"本科|学士|优秀本科", text):
        return None
    if re.search(r"[1-9一二三五十]+\s*年(?:以上)?(?:的)?(?:销售|相关|工作)经验", text):
        return None
    if re.search(r"202[0-6]届", job.title) and not re.search(r"2027|27届", text):
        return None
    if re.search(r"门店|导购|置业顾问|保险代理|房产经纪|零售销售", job.title):
        return None
    campaign = bool(CAMPAIGN.search(job.title))
    if not campaign and not SALES.search(job.title):
        return None
    bachelor = bool(re.search(r"本科|学士|大专|学历不限", job.description))
    unrestricted = bool(re.search(r"专业(?:不限|不设限)|不限专业|所有专业", job.description)) and not re.search(r"(?:不是|非|不视为|并非)专业不限", job.description)
    architecture = bool(re.search(r"建筑(?:学|类|相关)|专业[^。\n]*理工", job.description))
    mandatory_text = re.sub(r"非必须|不是必须|并非必须", "", job.description)
    preferred_only = bool(re.search(r"专业[^。；;\n]*优先", job.description)) and not re.search(r"必须|仅限|限定", mandatory_text)
    eligible = not campaign and bachelor and (unrestricted or architecture or preferred_only) and "公告列出" not in job.title and not re.search(r"需HR确认|需确认本科|需核对", job.description)
    return {
        "kind": "lead" if campaign else "job",
        "eligibility": "eligible" if eligible else "needs_confirmation",
        "requirements": "本科，专业不限" if eligible and unrestricted else (
            "本科；相关专业优先而非必须，建筑背景可尝试" if eligible else
            "需核对具体岗位的学历、专业与届别；公告不代表所有岗位可投"
        ),
    }


def build_sales(source_jobs: dict[str, list[RawJob]], config_path: Path,
                output: Path, today: date) -> dict:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    companies = [(name, industry) for industry, names in config["industries"].items() for name in names]
    aliases = config.get("aliases", {})
    old = json.loads(output.read_text(encoding="utf-8")) if output.exists() else {}
    # Absence, failed requests and empty lists are not proof of closure.
    records = {row["id"]: row for row in old.get("jobs", []) + old.get("leads", [])}
    observed = {name: [] for name, _ in companies}
    for rows in source_jobs.values():
        for job in [item for row in rows for item in [row, *expand_campaign(row)]]:
            canonical = next((name for name, _ in companies if any(
                alias.lower() in job.company.lower() for alias in [name, *aliases.get(name, [])]
            )), None)
            if not canonical:
                continue
            observed[canonical].append(job.detail_url)
            decision = classify_sales(job)
            industry = dict(companies)[canonical]
            title = re.sub(r"\s+", " ", job.title).strip()
            key = hashlib.sha256((canonical + title + '|'.join(sorted(job.location))).encode()).hexdigest()[:20]
            if job.official_status == "closed" or (job.deadline and job.deadline < today):
                records.pop(key, None)
                continue
            if decision is None:
                continue
            row = {
                "id": key, "company": canonical, "industry": industry, "title": title,
                "location": job.location, "detail_url": job.detail_url,
                "apply_url": job.official_apply_url or job.apply_url,
                "deadline": job.deadline.isoformat() if job.deadline else None,
                "publish_date": job.publish_date.isoformat() if job.publish_date else None,
                "first_seen": records.get(key, {}).get("first_seen", today.isoformat()),
                "source_id": job.source_id, "source_name": job.source_name or job.source_id,
                "verification": job.verification_status, "salary": job.salary_text or "未公布（底薪、提成与达标条件需确认）",
                **decision,
            }
            # Reviewed job records must not be downgraded by aggregate campaign data.
            records[key] = row
    records = {key: row for key, row in records.items() if not row.get("deadline") or row["deadline"] >= today.isoformat()}
    reviewed = [row for row in records.values() if "公告列出" not in row["title"] and row["kind"] == "job"]
    records = {key: row for key, row in records.items() if "公告列出" not in row["title"] or (
        not re.search(r"类$|方向$|族$|岗位$|//", row["title"].split("（2027公告列出）")[0]) and
        ROLE.search(row["title"]) and not any(
            other["company"] == row["company"] and role_name(row["title"]) in role_name(other["title"])
            for other in reviewed
        )
    )}
    jobs = sorted((row for row in records.values() if row["kind"] == "job"), key=lambda row: (
        row["eligibility"] != "eligible", row["verification"] == "pending", row["company"], row["title"]))
    leads = sorted((row for row in records.values() if row["kind"] == "lead"), key=lambda row: row["company"])
    previous_audit = {row["company"]: row for row in old.get("companies", [])}
    audit = []
    for name, industry in companies:
        matches = [row for row in jobs if row["company"] == name]
        announcements = [row for row in leads if row["company"] == name]
        prior = previous_audit.get(name, {})
        audit.append({
            "company": name, "industry": industry, "job_count": len(matches),
            "lead_count": len(announcements),
            "checked_date": today.isoformat() if source_jobs else prior.get("checked_date"),
            "status": "已找到销售岗位" if matches else ("有销售方向公告，需核验" if announcements else (
                "发现校招，但未发现匹配销售岗" if observed[name] else "配置来源暂未发现，非断言没有招聘")),
            "sources": list(dict.fromkeys(config.get("reviewed_sources", {}).get(name, []) + observed[name] + prior.get("sources", [])))[:5],
            "search_url": "https://www.bing.com/search?q=" + quote(name + " 2027 校园招聘 销售 客户经理 本科"),
        })
    payload = {"updated": today.isoformat(), "scope": "2027届本科ToB销售；不承诺全网覆盖", "jobs": jobs, "leads": leads, "companies": audit}
    encoded = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    output.parent.mkdir(parents=True, exist_ok=True)
    if not output.exists() or output.read_text(encoding="utf-8") != encoded:
        output.write_text(encoded, encoding="utf-8")
    return payload
