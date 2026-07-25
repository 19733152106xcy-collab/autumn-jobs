import json
from datetime import date


def test_pipeline_filters_deduplicates_and_writes_public_json(tmp_path):
    from autumn_jobs.models import RawJob
    from autumn_jobs.pipeline import run_pipeline

    source_jobs = {
        "cadg": [
            RawJob(
                source_id="cadg",
                company="中国建筑设计研究院有限公司",
                title="建筑设计岗",
                location=["北京"],
                detail_url="https://official.example.cn/job/1?utm_source=test",
                apply_url="https://official.example.cn/apply/1",
                description="2027届本科，建筑学及相关专业",
            )
        ],
        "zju": [
            RawJob(
                source_id="zju",
                company="中国建筑设计研究院",
                title="建筑设计岗",
                location=["北京"],
                detail_url="https://copy.example.cn/job/1",
                description="2027届本科，建筑学及相关专业",
            )
        ],
    }

    result = run_pipeline(source_jobs, tmp_path / "state", tmp_path / "site", date(2026, 7, 25))
    payload = json.loads((tmp_path / "site/data/jobs.json").read_text(encoding="utf-8"))

    assert result.publish_required is True
    assert len(payload["jobs"]) == 1
    assert payload["jobs"][0]["apply_url"] == "https://official.example.cn/apply/1"
    assert "description" not in payload["jobs"][0]


def test_identical_business_data_does_not_republish(tmp_path):
    from autumn_jobs.models import RawJob
    from autumn_jobs.pipeline import run_pipeline

    source_jobs = {
        "cadg": [
            RawJob(
                source_id="cadg",
                company="某设计院",
                title="建筑设计岗",
                location=["西安"],
                detail_url="https://example.cn/job/1",
                description="2027届本科，建筑学相关专业",
            )
        ]
    }
    first = run_pipeline(source_jobs, tmp_path / "state", tmp_path / "site", date(2026, 7, 25))
    mtime = first.public_path.stat().st_mtime_ns
    second = run_pipeline(source_jobs, tmp_path / "state", tmp_path / "site", date(2026, 7, 26))

    assert second.publish_required is False
    assert second.public_path.stat().st_mtime_ns == mtime
