#!/usr/bin/env python3

import sys
from pathlib import Path
from subprocess import run


def main():
    input_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("output/layer2-tests")

    if not input_dir.exists():
        print(f"[ERRO] Diretoria não existe: {input_dir}")
        return 2

    files = sorted(input_dir.glob("*.layer2.json"))

    if not files:
        print(f"[ERRO] Nenhum ficheiro .layer2.json encontrado em {input_dir}")
        return 2

    passed = 0
    failed = 0

    for path in files:
        print(f"\n==> {path}")

        result = run(
            ["python3", "scripts/ontology/export_layer2_to_rdf.py", str(path)],
            text=True,
        )

        if result.returncode == 0:
            passed += 1
        else:
            failed += 1

    print("\n==============================")
    print(f"EXPORTADOS: {passed}")
    print(f"FALHARAM:   {failed}")
    print("==============================")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())