from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from autumn_jobs.availability import is_active_job
from autumn_jobs.deduplication import deduplicate_jobs
from autumn_jobs.matching import classify_opportunity, match_job
from autumn_jobs.models import JobBusiness, PipelineResult, RawJob
from autumn_jobs.normalization import (
    make_fingerprint,
    normalize_company,
    normalize_locations,
    normalize_title,
    normalize_url,
)
from autumn_jobs.scoring import score_job
from autumn_jobs.state import load_jobs, write_jobs


def _priority(matched, raw: RawJob) -> tuple[int, str]:
    if (
        matched.job_group == "architecture"
        and matched.level == "A"
        and raw.opportunity_type == "full_time"
        and raw.verification_status in {"official", "verified"}
    ):
        return 1, "优先投"
    if matched.job_group == "architecture" and raw.opportunity_type != "internship":
        return 2, "值得投"
    if matched.job_group == "other":
        return 3, "跨行尝试"
    return 4, "备选关注"


def _to_business(raw: RawJob, today: date) -> JobBusiness | None:
    if not is_active_job(raw, today):
        return None
    matched = match_job(raw.title, raw.description)
    if not matched.included:
        return None
    company = normalize_company(raw.company)
    title = normalize_title(raw.title)
    locations = normalize_locations(raw.location)
    priority_rank, priority_label = _priority(matched, raw)
    scoring = score_job(raw, matched)
    return JobBusiness(
        fingerprint=make_fingerprint(company, title, locations),
        source_id=raw.source_id,
        source_job_id=raw.source_job_id,
        company=company,
        title=title,
        location=locations,
        deadline=raw.deadline,
        publish_date=raw.publish_date,
        first_seen=today,
        category=matched.category or "其他",
        match_level=matched.level or "C",
        job_group=matched.job_group or "other",
        priority_rank=priority_rank,
        priority_label=priority_label,
        match_reasons=matched.reasons,
        requirements=matched.requirements,
        apply_url=normalize_url(raw.apply_url) if raw.apply_url else None,
        detail_url=normalize_url(raw.detail_url),
        source_type=raw.source_type,
        verification_status=raw.verification_status,
        source_name=raw.source_name,
        official_apply_url=normalize_url(raw.official_apply_url) if raw.official_apply_url else None,
        opportunity_type=classify_opportunity(raw.title, raw.description),
        **scoring.model_dump(),
    )


def _public_payload(jobs: list[JobBusiness], today: date) -> dict[str, object]:
    public_fields = [
        "fingerprint", "company", "title", "location", "deadline", "publish_date", "first_seen",
        "category", "match_level", "apply_url", "detail_url", "source_type", "verification_status",
        "source_name", "official_apply_url", "opportunity_type", "job_group", "priority_rank",
        "priority_label", "status",
        "eligibility_status", "eligibility_label", "score_total", "score_breakdown",
        "salary_band", "salary_basis", "score_confidence", "score_summary",
        "score_strengths", "score_risks",
    ]
    rows = [{field: job.model_dump(mode="json")[field] for field in public_fields} for job in jobs if job.status == "active"]
    rows.sort(key=lambda row: (row["first_seen"], row["company"], row["title"]), reverse=True)
    return {"updated_date": today.isoformat(), "jobs": rows}


def run_pipeline(
    source_jobs: dict[str, list[RawJob]],
    successful_source_ids: set[str],
    state_dir: Path,
    site_dir: Path,
    today: date,
) -> PipelineResult:
    state_path = state_dir / "jobs.json"
    previous = load_jobs(state_path)
    previous_first_seen = {job.fingerprint: job.first_seen for job in previous}
    incoming = [_to_business(raw, today) for jobs in source_jobs.values() for raw in jobs]
    current = [job for job in incoming if job is not None]
    for index, job in enumerate(current):
        if job.fingerprint in previous_first_seen:
            current[index] = job.model_copy(update={"first_seen": previous_first_seen[job.fingerprint]})
    current = deduplicate_jobs(current)
    preserved = [job for job in previous if job.source_id not in successful_source_ids]
    combined = deduplicate_jobs(preserved + current)
    payload = _public_payload(combined, today)
    public_path = site_dir / "data" / "jobs.json"
    existing = json.loads(public_path.read_text(encoding="utf-8")) if public_path.exists() else None
    comparison = {"jobs": payload["jobs"]}
    existing_comparison = {"jobs": existing.get("jobs", [])} if existing else None
    changed = comparison != existing_comparison
    if changed:
        write_jobs(state_path, combined)
        public_path.parent.mkdir(parents=True, exist_ok=True)
        public_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (site_dir / "data" / "update_status.json").write_text(
            json.dumps({"updated_date": today.isoformat(), "active_jobs": len(payload["jobs"])}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return PipelineResult(
        publish_required=changed,
        public_path=public_path,
        jobs_count=len(payload["jobs"]),
        duplicate_count=max(0, len(incoming) - len(current)),
    )
