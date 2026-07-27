from __future__ import annotations

from datetime import date

from autumn_jobs.models import RawJob


def is_active_job(job: RawJob, today: date) -> bool:
    if job.deadline is not None and job.deadline < today:
        return False
    return job.official_status != "closed"
