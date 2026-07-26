from pathlib import Path

import yaml


def test_extract_job_links_prefers_recruitment_anchors():
    from autumn_jobs.sources import extract_job_links

    html = """
    <a href='/news'>公司新闻</a>
    <a href='/jobs/1'>2027届建筑设计岗校园招聘</a>
    <a href='/jobs/2'>AI解决方案助理</a>
    <a href='/showcase/bim'>BIM</a>
    <a href='/career/2025-campus'>2025届校园招聘</a>
    """

    links = extract_job_links("https://example.cn", html, 10)

    assert links == [
        ("2027届建筑设计岗校园招聘", "https://example.cn/jobs/1"),
        ("AI解决方案助理", "https://example.cn/jobs/2"),
    ]


def test_enabled_source_configuration_is_valid_yaml():
    config = yaml.safe_load(Path("config/sources.yaml").read_text(encoding="utf-8"))

    assert len(config["sources"]) == 10
    assert all(source["url"].startswith("https://") for source in config["sources"])


def test_legacy_cccec_source_is_disabled_when_cscec8_adapter_covers_it():
    config = yaml.safe_load(Path("config/sources.yaml").read_text(encoding="utf-8"))
    cccec = next(source for source in config["sources"] if source["id"] == "cccec")

    assert cccec["enabled"] is False
    assert Path("config/cscec8.yaml").exists()


def test_extract_role_rows_turns_a_recruitment_table_into_specific_jobs():
    from autumn_jobs.sources import extract_role_rows

    text = "岗位名称 学历 人数 经验 详情 助理规划设计师 研究生 若干 应届生 申请该职位 助理建筑设计师 本科 若干 应届生"

    assert extract_role_rows(text) == [
        ("助理规划设计师", "学历：研究生"),
        ("助理建筑设计师", "学历：本科"),
    ]
