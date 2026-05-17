#!/usr/bin/env python3

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "output"
RDF_DIR = OUTPUT_DIR / "rdf"


def find_layer2_jsons(root: Path) -> list[Path]:
    files = []

    for path in root.rglob("*.layer2.json"):
        parts = set(path.parts)

        # Evitar outputs que não fazem parte da entrada do pipeline.
        if "rdf" in parts or "issues" in parts or "architecture" in parts:
            continue

        files.append(path)

    return sorted(files)


def make_stem(json_path: Path, root: Path) -> str:
    """
    Gera um nome estável para o RDF a partir do path relativo.

    Exemplos:
      output/robot.launch.layer2.json
        -> robot.launch

      output/layer2-tests/node.launch.py.layer2.json
        -> layer2-tests__node.launch.py
    """
    rel = json_path.relative_to(root)

    name = str(rel)

    if name.endswith(".layer2.json"):
        name = name[:-len(".layer2.json")]

    return name.replace(os.sep, "__")


def run_command(cmd: list[str]) -> None:
    subprocess.run(
        cmd,
        cwd=str(PROJECT_ROOT),
        check=True,
        text=True,
    )


def run_command_capture(cmd: list[str]) -> str:
    result = subprocess.run(
        cmd,
        cwd=str(PROJECT_ROOT),
        check=True,
        text=True,
        capture_output=True,
    )

    if result.stderr:
        print(result.stderr.rstrip(), file=sys.stderr)

    return result.stdout


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else OUTPUT_DIR

    if not root.is_absolute():
        root = PROJECT_ROOT / root

    if not root.exists():
        print(f"[ERRO] Pasta não encontrada: {root}")
        return 1

    RDF_DIR.mkdir(parents=True, exist_ok=True)

    json_files = find_layer2_jsons(root)

    if not json_files:
        print(f"[AVISO] Nenhum ficheiro .layer2.json encontrado em: {root}")
        return 0

    print(f"[INFO] Ficheiros Layer 2 encontrados: {len(json_files)}")
    print(f"[INFO] RDF output: {RDF_DIR}")

    total_ontology_issues = 0

    for json_path in json_files:
        stem = make_stem(json_path, OUTPUT_DIR)
        rdf_path = RDF_DIR / f"{stem}.layer2.ttl"

        print()
        print(f"[PIPELINE] {json_path.relative_to(PROJECT_ROOT)}")
        print(f"  -> RDF: {rdf_path.relative_to(PROJECT_ROOT)}")

        run_command([
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "ontology" / "export_layer2_to_rdf.py"),
            str(json_path),
            str(rdf_path),
        ])

        stdout = run_command_capture([
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "ontology" / "run_ontology_issues.py"),
            str(rdf_path),
        ])

        if stdout:
            print(stdout.rstrip())

        for line in stdout.splitlines():
            if line.startswith("[OK] Issues ontológicos:"):
                total_ontology_issues += int(line.split(":")[-1].strip())

    print()
    print("=" * 70)
    print("[OK] Pipeline ontológico concluído")
    print(f"[OK] Ficheiros processados: {len(json_files)}")
    print(f"[OK] Issues ontológicos totais: {total_ontology_issues}")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())