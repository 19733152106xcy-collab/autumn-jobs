from autumn_jobs.matching import match_job


def test_doctoral_special_program_is_excluded_for_an_undergraduate_profile():
    result = match_job(
        "华中公司2027届校园招聘-水利博士专项计划",
        "智能建造方向。",
    )

    assert result.included is False
