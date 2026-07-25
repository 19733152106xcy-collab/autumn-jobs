from __future__ import annotations

from collections import defaultdict

from autumn_jobs.models import JobBusiness
from autumn_jobs.normalization import normalize_company, normalize_locations, normalize_title


def _key(job: JobBusiness) -> tuple[str, str, tuple[str, ...]]:
    return normalize_company(job.company), normalize_title(job.title), tuple(normalize_locations(job.location))


def deduplicate_jobs(jobs: list[JobBusiness]) -> list[JobBusiness]:
    groups: dict[tuple[str, str, tuple[str, ...]], list[JobBusiness]] = defaultdict(list)
    for job in jobs:
        groups[_key(job)].append(job)
    merged: list[JobBusiness] = []
    for group in groups.values():
        by_official_id = {job.source_job_id for job in group if job.source_job_id}
        if len(by_official_id) > 1:
            merged.extend(group)
            continue
        primary = next((job for job in group if job.apply_url), group[0]).model_copy(deep=True)
        for duplicate in group:
            if duplicate is primary:
                continue
            if duplicate.detail_url != primary.detail_url and duplicate.detail_url not in primary.alternate_sources:
                primary.alternate_sources.append(duplicate.detail_url)
            if not primary.apply_url and duplicate.apply_url:
                primary.apply_url = duplicate.apply_url
        merged.append(primary)
    return merged
