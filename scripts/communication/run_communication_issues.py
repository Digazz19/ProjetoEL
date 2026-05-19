#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from issues.io import write_issues_json
from issues.ontology_detector import OntologyIssueDetector


COMMUNICATION_QUERY_KEYS = [
    "isolated_node",
    "publisher_without_subscriber",
    "subscriber_without_publisher",
    "topic_multiple_publishers",
    "qos_reliability_mismatch",
    "message_type_mismatch",
]


def output_path_for(rdf_path: str) -> str:
    base = os.path.basename(rdf_path)

    if base.endswith(".architecture.ttl"):
        stem = base[:-len(".architecture.ttl")]
    else:
        stem = os.path.splitext(base)[0]

    return os.path.join("output", "issues", f"{stem}.communication.issues.json")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Gera issues de comunicação a partir de RDF de RuntimeArchitecture."
    )
    parser.add_argument("architecture_rdf")
    parser.add_argument(
        "-o",
        "--output",
        help="Caminho de output. Por omissão: output/issues/<nome>.communication.issues.json",
    )

    args = parser.parse_args()

    rdf_path = args.architecture_rdf

    if not os.path.exists(rdf_path):
        print(f"[ERRO] RDF de arquitetura não encontrado: {rdf_path}")
        return 1

    detector = OntologyIssueDetector(
        query_dir="ontology/queries/communication",
        query_keys=COMMUNICATION_QUERY_KEYS,
    )

    issues = detector.detect_from_file(rdf_path)

    out_path = args.output or output_path_for(rdf_path)
    write_issues_json(issues, out_path)

    print(f"[OK] RDF de arquitetura analisado: {rdf_path}")
    print(f"[OK] Issues de comunicação: {len(issues)}")
    print(f"[OK] JSON guardado em: {out_path}")

    for issue in issues:
        print(f"  [{issue.severity.upper():8s}] {issue.description}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())