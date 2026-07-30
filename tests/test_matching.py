from autumn_jobs.matching import match_job


def test_excludes_water_supply_but_keeps_project_management():
    assert match_job("水暖工程岗", "2027届本科建筑相关专业").included is False
    assert match_job("项目管理岗", "2027届本科建筑相关专业").included is True


def test_outputs_architecture_and_other_groups():
    assert match_job("建筑设计师", "2027届本科建筑学").job_group == "architecture"
    assert match_job("AI产品助理", "2027届本科专业不限").job_group == "other"


def test_classifies_a_summer_internship_as_an_internship_opportunity():
    from autumn_jobs.matching import classify_opportunity

    assert classify_opportunity("中建八局二公司2027届暑期实习招聘", "") == "internship"


def test_classifies_a_combined_campus_and_internship_notice_as_mixed():
    from autumn_jobs.matching import classify_opportunity

    assert classify_opportunity("2026届校园招聘&2027届实习生招聘", "") == "mixed"


def test_doctoral_special_program_is_excluded_for_an_undergraduate_profile():
    result = match_job(
        "华中公司2027届校园招聘-水利博士专项计划",
        "智能建造方向。",
    )

    assert result.included is False
