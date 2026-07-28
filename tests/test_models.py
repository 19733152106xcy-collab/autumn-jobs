from autumn_jobs.models import RawJob


def test_raw_job_defaults_to_a_pending_public_announcement():
    job = RawJob(
        source_id="bucea",
        company="某设计院",
        title="建筑设计岗2027届校园招聘",
        location=["北京"],
        detail_url="https://job.bucea.edu.cn/front/zwxx.jspa?id=1",
        description="2027届本科，建筑学相关专业",
    )

    assert job.source_type == "public_article"
    assert job.verification_status == "pending"
    assert job.source_name is None
    assert job.official_apply_url is None
