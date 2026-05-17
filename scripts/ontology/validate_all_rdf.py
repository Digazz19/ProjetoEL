#!/usr/bin/env python3

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RDF_DIR = PROJECT_ROOT / "output" / "rdf"
VALIDATE_RDF = PROJECT_ROOT / "scripts" / "ontology" / "validate_rdf.py"


def find_rdf_files(root: Path) -> list[Path]:
    if not root.exists():
        return []

    files = []

    for path in root.rglob("*.ttl"):
        # Só validar os RDFs Layer 2 nesta demo principal.
        # Os RDFs de arquitetura runtime ficam em output/rdf/architecture
        # e podem ter shapes próprias no futuro.
        if "architecture" in path.parts:
            continue

        files.append(path)

    return sorted(files)


def main() -> int:
    rdf_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else RDF_DIR

    if not rdf_dir.is_absolute():
        rdf_dir = PROJECT_ROOT / rdf_dir

    if not rdf_dir.exists():
        print(f"[ERRO] Pasta RDF não encontrada: {rdf_dir}")
        return 1

    if not VALIDATE_RDF.exists():
        print(f"[ERRO] Script validate_rdf.py não encontrado: {VALIDATE_RDF}")
        return 1

    rdf_files = find_rdf_files(rdf_dir)

    if not rdf_files:
        print(f"[AVISO] Nenhum ficheiro .ttl encontrado em: {rdf_dir}")
        return 0

    valid = 0
    invalid = 0

    for rdf_path in rdf_files:
        print()
        print(f"==> {rdf_path.relative_to(PROJECT_ROOT)}")

        result = subprocess.run(
            [
                sys.executable,
                str(VALIDATE_RDF),
                str(rdf_path),
            ],
            cwd=str(PROJECT_ROOT),
            text=True,
        )

        if result.returncode == 0:
            valid += 1
        else:
            invalid += 1

    print()
    print("=" * 30)
    print(f"VÁLIDOS:  {valid}")
    print(f"INVÁLIDOS:{invalid}")
    print("=" * 30)

    return 0 if invalid == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())