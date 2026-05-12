#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from issues.graphdb_detector import GraphDBIssueDetector
from issues.io import write_issues_json


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Gera Issues Layer 6 a partir de queries SPARQL executadas no GraphDB."
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:7200",
    )
    parser.add_argument(
        "--repo",
        default="projetoel",
    )
    parser.add_argument(
        "--output",
        default="output/issues/graphdb.issues.json",
    )

    args = parser.parse_args()

    detector = GraphDBIssueDetector(
        base_url=args.base_url,
        repo=args.repo,
    )

    issues = detector.detect()
    write_issues_json(issues, args.output)

    print(f"[OK] Issues GraphDB: {len(issues)}")
    print(f"[OK] JSON guardado em: {args.output}")

    for issue in issues:
        print(f"  [{issue.severity.upper():8s}] {issue.description}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())