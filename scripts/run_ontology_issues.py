#!/usr/bin/env python3

from __future__ import annotations

import os
import sys
from pathlib import Path

# Permite correr o script diretamente a partir da raiz do projeto.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from issues.io import write_issues_json
from issues.ontology_detector import OntologyIssueDetector


def output_path_for(rdf_path: str) -> str:
    base = os.path.basename(rdf_path)

    if base.endswith(".layer2.ttl"):
        stem = base[:-len(".layer2.ttl")]
    else:
        stem = os.path.splitext(base)[0]

    return os.path.join("output", "issues", f"{stem}.ontology.issues.json")


def main() -> int:
    if len(sys.argv) < 2:
        print("Uso:")
        print("  python3 scripts/run_ontology_issues.py output/rdf/robot.launch.layer2.ttl")
        return 1

    rdf_path = sys.argv[1]

    if not os.path.exists(rdf_path):
        print(f"[ERRO] RDF não encontrado: {rdf_path}")
        return 1

    detector = OntologyIssueDetector()
    issues = detector.detect_from_file(rdf_path)

    out_path = output_path_for(rdf_path)
    write_issues_json(issues, out_path)

    print(f"[OK] RDF analisado: {rdf_path}")
    print(f"[OK] Issues ontológicos: {len(issues)}")
    print(f"[OK] JSON guardado em: {out_path}")

    for issue in issues:
        print(f"  [{issue.severity.upper():8s}] {issue.description}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())