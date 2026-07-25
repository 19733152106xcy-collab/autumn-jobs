from pathlib import Path


def test_audit_requires_evidence_for_every_candidate():
    from autumn_jobs.audit import load_audit

    rows = load_audit(Path("docs/source-audit.json"))

    assert len(rows) == 10
    assert all(row.final_url and row.checked_at for row in rows)
    assert all(row.access in {"public", "partial", "blocked"} for row in rows)
    assert all(row.robots_checked for row in rows if row.access != "blocked")
    assert all(row.error_code for row in rows if row.access == "blocked")
