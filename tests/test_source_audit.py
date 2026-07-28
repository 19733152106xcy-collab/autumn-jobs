from pathlib import Path

import yaml

from autumn_jobs.audit import AuditRow


def test_audit_requires_evidence_for_every_candidate():
    from autumn_jobs.audit import load_audit

    rows = load_audit(Path("docs/source-audit.json"))

    candidates = yaml.safe_load(Path("config/source_candidates.yaml").read_text(encoding="utf-8"))
    candidate_ids = {candidate["id"] for candidate in candidates["candidates"]}
    audited_ids = {row.source_id for row in rows}

    assert candidate_ids <= audited_ids
    assert "cscec8" in audited_ids
    assert all(row.final_url and row.checked_at for row in rows)
    assert all(row.access in {"public", "partial", "blocked"} for row in rows)
    assert all(row.robots_checked for row in rows if row.access != "blocked")
    assert all(row.error_code for row in rows if row.access == "blocked")


def test_merge_audit_replaces_only_reaudited_source_ids():
    from autumn_jobs.audit import merge_audit

    previous = [
        AuditRow("cscec8", "https://official.example/c8", "2026-07-27T00:00:00+00:00", "public", "json_api", True, True, False, True),
        AuditRow("cadg", "https://official.example/cadg", "2026-07-27T00:00:00+00:00", "partial", "html", True, False, True, True),
    ]
    current = [
        AuditRow("bucea", "https://job.bucea.edu.cn/", "2026-07-28T00:00:00+00:00", "public", "html", True, True, False, True),
        AuditRow("cadg", "https://official.example/cadg/new", "2026-07-28T00:00:00+00:00", "public", "html", True, True, False, True),
    ]

    merged = merge_audit(previous, current)

    assert [row.source_id for row in merged] == ["cscec8", "cadg", "bucea"]
    assert next(row for row in merged if row.source_id == "cadg").final_url.endswith("/new")
