from datetime import date

from autumn_jobs.deduplication import deduplicate_jobs
from autumn_jobs.models import JobBusiness, StructuredRequirements


def make_job(**changes: object) -> JobBusiness:
    values: dict[str, object] = {
        "fingerprint": "same-job",
        "source_id": "source",
        "company": "某设计院",
        "title": "建筑设计岗2027届校园招聘",
        "location": ["北京"],
        "first_seen": date(2026, 7, 28),
        "category": "建筑设计",
        "match_level": "A",
        "match_reasons": ["建筑设计"],
        "requirements": StructuredRequirements(),
        "detail_url": "https://example.test/detail",
        "apply_url": "https://example.test/apply",
    }
    values.update(changes)
    return JobBusiness(**values)


def test_deduplication_prefers_official_application_url():
    official = make_job(
        source_id="cscec8",
        detail_url="https://official.example/job/8",
        apply_url="https://official.example/apply/8",
        verification_status="official",
        source_type="official",
    )
    pending = make_job(
        source_id="guopinleida",
        detail_url="https://guopinleida.com/jobs/8",
        apply_url="https://guopinleida.com/jobs/8",
        verification_status="pending",
        source_type="job_board",
    )

    merged = deduplicate_jobs([pending, official])

    assert len(merged) == 1
    assert merged[0].verification_status == "official"
    assert merged[0].detail_url == "https://official.example/job/8"
