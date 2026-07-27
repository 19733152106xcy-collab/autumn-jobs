from pathlib import Path

import yaml


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
