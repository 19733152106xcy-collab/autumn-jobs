import pytest

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


@pytest.mark.parametrize(
    "title",
    [
        "景观设计师",
        "园林设计岗",
        "风景园林岗",
        "土木工程师",
        "结构设计师",
        "道路工程师",
        "桥梁工程师",
    ],
)
def test_excludes_non_architecture_specialties_even_when_architecture_is_mentioned(title):
    assert match_job(title, "2027届本科，建筑学及相关专业可投").included is False


def test_related_role_requires_an_eligible_major_signal():
    assert match_job("项目管理岗", "2027届本科，土木类专业").included is False
    assert match_job("项目管理岗", "2027届本科，工程类专业").included is True


def test_description_from_other_roles_does_not_change_current_job_direction():
    assert match_job("营销专员", "同时招聘建筑设计、项目管理岗位").included is False


def test_excludes_postgraduate_only_but_keeps_postgraduate_preferred():
    assert match_job("建筑设计岗", "硕士及以上学历，建筑学专业").included is False
    assert match_job("建筑设计岗", "研究生及以上学历，建筑学专业").included is False
    assert match_job("建筑设计岗", "建筑学专业，硕士学历").included is False
    assert match_job("建筑设计岗", "本科及以上，硕士优先，建筑学专业").included is True


def test_excludes_teacher_roles_without_relying_on_missing_degree_data():
    assert match_job("城乡规划学专业教师岗位", "建筑学相关专业").included is False


def test_generic_2027_campaign_uses_relevant_body_roles_for_cross_industry_matching():
    result = match_job(
        "彩讯2027校园招聘 RICH AI+人才计划",
        "管培生，包含产品与项目方向、设计方向，本科应届生，专业不限",
    )

    assert result.included is True
    assert result.job_group == "other"


def test_teaching_management_trainee_is_not_included_as_a_generic_cross_industry_role():
    result = match_job(
        "新东方2027届管培生提前批招募",
        "教学管培生、课程顾问，专业不限，本科应届生",
    )

    assert result.included is False


def test_2026_campaign_without_2027_cohort_is_excluded():
    result = match_job(
        "FMC Consulting 2026校园招聘全面启动",
        "项目管培生，本科，专业不限",
    )

    assert result.included is False
    assert match_job(
        "申洲2026春季全球校园招聘正式启动",
        "运营管培生，本科，专业不限",
    ).included is False


def test_training_company_campaign_with_teaching_directions_is_excluded():
    result = match_job(
        "极客未来2027秋季校园招聘提前批全面启动",
        "小学班课主讲教师、学科校长管培生（教学方向），专业不限",
    )

    assert result.included is False
