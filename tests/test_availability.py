from datetime import date

from autumn_jobs.models import RawJob


def make_job(**changes: object) -> RawJob:
    values: dict[str, object] = {
        "source_id": "official",
        "company": "某设计院",
        "title": "建筑设计岗2027届校园招聘",
        "location": ["西安"],
        "detail_url": "https://official.example/jobs/17",
        "description": "2027届本科，建筑学及相关专业",
    }
    values.update(changes)
    return RawJob(**values)


def test_expired_job_is_not_active():
    from autumn_jobs.availability import is_active_job

    assert is_active_job(make_job(deadline=date(2026, 7, 26)), date(2026, 7, 27)) is False


def test_official_closed_marker_is_not_active():
    from autumn_jobs.availability import is_active_job

    assert is_active_job(make_job(official_status="closed"), date(2026, 7, 27)) is False


def test_unknown_or_suspect_job_stays_active():
    from autumn_jobs.availability import is_active_job

    assert is_active_job(make_job(official_status="unknown"), date(2026, 7, 27)) is True
    assert is_active_job(make_job(official_status="suspect"), date(2026, 7, 27)) is True
