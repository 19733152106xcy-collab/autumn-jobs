from autumn_jobs.sources import load_verified_jobs


def test_verified_jobs_loads_a_public_official_job(tmp_path):
    config = tmp_path / "verified_jobs.yaml"
    config.write_text(
        """jobs:
  - source_id: cscec8_design
    company: 中建八局设计管理总院
    title: 设计管理总院2027届校园招聘
    location: [上海浦东新区]
    apply_url: https://job.cscec8b.com.cn/8bsjzy
    detail_url: https://job.cscec8b.com.cn/8bsjzy
    publish_date: 2026-06-18
    description: 2027届大学本科及以上学历，建筑学专业
""",
        encoding="utf-8",
    )

    [job] = load_verified_jobs(config)

    assert job.company == "中建八局设计管理总院"
    assert job.publish_date.isoformat() == "2026-06-18"
    assert job.apply_url == "https://job.cscec8b.com.cn/8bsjzy"
