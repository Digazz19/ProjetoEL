#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from issues.io import write_issues_json
from issues.ontology_detector import OntologyIssueDetector
from scripts.build_runtime_architecture import build_architecture
from scripts.export_architecture_to_rdf import architecture_json_to_graph


COMMUNICATION_QUERY_KEYS = [
    "isolated_node",
    "publisher_without_subscriber",
    "subscriber_without_publisher",
    "topic_multiple_publishers",
    "qos_reliability_mismatch",
]


def stem_from_layer2(layer2_path: Path) -> str:
    base = layer2_path.name

    if base.endswith(".layer2.json"):
        return base[:-len(".layer2.json")]

    return layer2_path.stem


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Pipeline completa de comunicação: "
            "Layer 2 JSON + anotações YAML -> RuntimeArchitecture -> RDF -> Issues."
        )
    )
    parser.add_argument("layer2_json")
    parser.add_argument("annotations_yaml")
    parser.add_argument(
        "--architecture-output",
        help="Output JSON da RuntimeArchitecture.",
    )
    parser.add_argument(
        "--rdf-output",
        help="Output RDF/Turtle da RuntimeArchitecture.",
    )
    parser.add_argument(
        "--issues-output",
        help="Output JSON dos issues de comunicação.",
    )

    args = parser.parse_args()

    layer2_path = Path(args.layer2_json)
    annotations_path = Path(args.annotations_yaml)

    if not layer2_path.exists():
        print(f"[ERRO] Layer 2 JSON não encontrado: {layer2_path}")
        return 1

    if not annotations_path.exists():
        print(f"[ERRO] Anotações não encontradas: {annotations_path}")
        return 1

    stem = stem_from_layer2(layer2_path)

    architecture_output = Path(
        args.architecture_output
        or Path("output") / "architecture" / f"{stem}.architecture.json"
    )

    rdf_output = Path(
        args.rdf_output
        or Path("output") / "rdf" / "architecture" / f"{stem}.architecture.ttl"
    )

    issues_output = Path(
        args.issues_output
        or Path("output") / "issues" / f"{stem}.communication.issues.json"
    )

    # ------------------------------------------------------------------
    # 1. Build RuntimeArchitecture JSON
    # ------------------------------------------------------------------

    architecture = build_architecture(layer2_path, annotations_path)

    architecture_output.parent.mkdir(parents=True, exist_ok=True)

    with architecture_output.open("w", encoding="utf-8") as f:
        json.dump(architecture.to_dict(), f, indent=2, ensure_ascii=False)

    print(f"[OK] Arquitetura gerada: {architecture_output}")
    print(f"[OK] Nodes: {len(architecture.nodes)}")
    print(f"[OK] Topics: {len(architecture.topics)}")
    print(f"[OK] Publications: {len(architecture.publications)}")
    print(f"[OK] Subscriptions: {len(architecture.subscriptions)}")

    if architecture.warnings:
        print(f"[AVISO] Warnings: {len(architecture.warnings)}")
        for warning in architecture.warnings:
            print(f"  - {warning}")

    # ------------------------------------------------------------------
    # 2. Export RDF/Turtle
    # ------------------------------------------------------------------

    graph = architecture_json_to_graph(architecture.to_dict())

    rdf_output.parent.mkdir(parents=True, exist_ok=True)
    graph.serialize(destination=str(rdf_output), format="turtle")

    print(f"[OK] RDF de arquitetura gerado: {rdf_output}")
    print(f"[OK] triples: {len(graph)}")

    # ------------------------------------------------------------------
    # 3. Run communication issues
    # ------------------------------------------------------------------

    detector = OntologyIssueDetector(
        query_dir="ontology/queries/communication",
        query_keys=COMMUNICATION_QUERY_KEYS,
    )

    issues = detector.detect_from_file(str(rdf_output))

    write_issues_json(issues, str(issues_output))

    print(f"[OK] Issues de comunicação: {len(issues)}")
    print(f"[OK] JSON guardado em: {issues_output}")

    for issue in issues:
        print(f"  [{issue.severity.upper():8s}] {issue.description}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())