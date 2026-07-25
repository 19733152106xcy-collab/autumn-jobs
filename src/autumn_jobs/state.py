from __future__ import annotations

import hashlib
import json
from pathlib import Path

from autumn_jobs.models import JobBusiness


def business_hash(job: JobBusiness) -> str:
    payload = json.dumps(job.model_dump(mode="json"), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_jobs(path: Path) -> list[JobBusiness]:
    if not path.exists():
        return []
    return [JobBusiness.model_validate(row) for row in json.loads(path.read_text(encoding="utf-8"))]


def write_jobs(path: Path, jobs: list[JobBusiness]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps([job.model_dump(mode="json") for job in jobs], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)
