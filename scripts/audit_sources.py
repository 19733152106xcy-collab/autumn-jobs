from __future__ import annotations

import argparse
from pathlib import Path

from autumn_jobs.audit import audit_candidates, load_audit, merge_audit, write_audit


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit configured public recruitment sources.")
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    previous = load_audit(args.output) if args.output.exists() else []
    write_audit(merge_audit(previous, audit_candidates(args.candidates)), args.output)


if __name__ == "__main__":
    main()
