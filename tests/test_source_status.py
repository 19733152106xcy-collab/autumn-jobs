from datetime import UTC, datetime

from autumn_jobs.sources import SourceHealth, update_source_status


def test_source_status_keeps_last_success_and_counts_consecutive_failures(tmp_path):
    path = tmp_path / "source_status.json"
    first = update_source_status(
        path,
        [
            SourceHealth(source_id="official", status="ok", discovered=3),
            SourceHealth(source_id="university", status="failed", discovered=0, error="ReadTimeout"),
        ],
        datetime(2026, 7, 25, 7, 30, tzinfo=UTC),
    )
    second = update_source_status(
        path,
        [
            SourceHealth(source_id="official", status="failed", discovered=0, error="HTTPStatusError"),
            SourceHealth(source_id="university", status="failed", discovered=0, error="ReadTimeout"),
        ],
        datetime(2026, 7, 26, 7, 30, tzinfo=UTC),
    )

    assert first["official"]["last_success"] == "2026-07-25T07:30:00+00:00"
    assert second["official"]["last_success"] == "2026-07-25T07:30:00+00:00"
    assert second["official"]["consecutive_failures"] == 1
    assert second["university"]["consecutive_failures"] == 2


def test_source_status_marks_a_large_discovery_drop_as_suspect(tmp_path):
    path = tmp_path / "source_status.json"
    update_source_status(
        path,
        [SourceHealth(source_id="official", status="ok", discovered=20)],
        datetime(2026, 7, 25, 7, 30, tzinfo=UTC),
    )

    result = update_source_status(
        path,
        [SourceHealth(source_id="official", status="ok", discovered=0)],
        datetime(2026, 7, 26, 7, 30, tzinfo=UTC),
    )

    assert result["official"]["status"] == "suspect"
    assert result["official"]["last_error"] == "DiscoveryDropToZero"
    assert result["official"]["consecutive_failures"] == 1
