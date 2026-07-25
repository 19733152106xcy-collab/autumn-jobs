from __future__ import annotations

import argparse
from pathlib import Path

from autumn_jobs.audit import audit_candidates, write_audit


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit configured public recruitment sources.")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_audit(audit_candidates(args.input), args.output)


if __name__ == "__main__":
    main()
