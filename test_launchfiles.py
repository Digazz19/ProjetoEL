"""
test_launchfiles.py

Testa o parser Python em todos os launch files .py encontrados
nas pastas indicadas, mostra um resumo e guarda os JSONs Layer 2
na pasta output/.

Uso:
    python3 test_launchfiles.py
    python3 test_launchfiles.py examples/real-python
    python3 test_launchfiles.py examples/real-python examples/outro
"""

import sys
import os

DEFAULT_DIRS = ["examples/real-python"]
OUTPUT_DIR = "output"


def build_parser():
    from parsers.python.parser import PythonLaunchParser
    return PythonLaunchParser()


def find_launch_files(dirs):
    files = []
    for d in dirs:
        if not os.path.exists(d):
            print(f"[AVISO] Pasta não encontrada: {d}")
            continue
        for root, _, filenames in os.walk(d):
            for f in sorted(filenames):
                if f.endswith(".launch.py") or (f.endswith(".py") and "launch" in f):
                    files.append(os.path.join(root, f))
    return sorted(files)


def test_file(parser, path):
    try:
        tree, ld = parser.parse(path)

        from models.layer2 import NodeAction, DeclareArgumentAction, IncludeAction
        nodes    = sum(1 for a in ld.actions.values()
                       if isinstance(a, NodeAction) and a.package
                       and a.package.value != "__executable__")
        args     = sum(1 for a in ld.actions.values() if isinstance(a, DeclareArgumentAction))
        includes = sum(1 for a in ld.actions.values() if isinstance(a, IncludeAction))

        # Guardar JSON em output/
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        base_name = os.path.splitext(os.path.basename(path))[0]
        json_path = os.path.join(OUTPUT_DIR, f"{base_name}.layer2.json")
        with open(json_path, "w", encoding="utf-8") as f:
            f.write(ld.to_json(indent=2))

        # Validação Layer 2
        from models.layer2 import Layer2Validator
        errors = Layer2Validator().validate(ld)

        return {
            "status": "OK",
            "nodes": nodes,
            "args": args,
            "includes": includes,
            "total_actions": len(ld.actions),
            "valid": len(errors) == 0,
            "validation_errors": len(errors),
            "json_path": json_path,
            "error": None,
        }

    except Exception as e:
        import re
        msg = str(e)
        m = re.search(r"line (\d+)[^\n]*col(?:umn)? (\d+)", msg)
        location = f" (linha {m.group(1)}, col {m.group(2)})" if m else ""
        return {
            "status": "ERRO",
            "nodes": 0, "args": 0, "includes": 0, "total_actions": 0,
            "valid": False, "validation_errors": 0, "json_path": None,
            "error": msg.split("\n")[0][:100] + location,
        }


def main():
    dirs = sys.argv[1:] if len(sys.argv) > 1 else DEFAULT_DIRS

    print(f"\n{'='*70}")
    print(f"  Teste do Parser Python — Layer 2")
    print(f"  Pastas: {', '.join(dirs)}")
    print(f"  JSONs em: {OUTPUT_DIR}/")
    print(f"{'='*70}\n")

    try:
        parser = build_parser()
    except Exception as e:
        print(f"[ERRO] Não foi possível inicializar o parser: {e}")
        sys.exit(1)

    files = find_launch_files(dirs)
    if not files:
        print("Nenhum launch file Python encontrado.")
        sys.exit(0)

    print(f"Ficheiros encontrados: {len(files)}\n")

    results = []
    for path in files:
        result = test_file(parser, path)
        results.append((path, result))

        name = os.path.relpath(path)
        if result["status"] == "OK":
            valid_str = "✓" if result["valid"] else f"✗ ({result['validation_errors']} erros)"
            print(f"  ✓  {name}")
            print(f"       acções={result['total_actions']}  nodes={result['nodes']}  "
                  f"args={result['args']}  includes={result['includes']}  "
                  f"validação={valid_str}")
            print(f"       → {result['json_path']}")
        else:
            print(f"  ✗  {name}")
            print(f"       {result['error']}")

    ok  = [(p, r) for p, r in results if r["status"] == "OK"]
    err = [(p, r) for p, r in results if r["status"] == "ERRO"]

    print(f"\n{'='*70}")
    print(f"  RESULTADO: {len(ok)}/{len(results)} ficheiros OK")
    print(f"{'='*70}")

    if err:
        print(f"\nFicheiros com erro ({len(err)}):")
        for path, result in err:
            print(f"  - {os.path.relpath(path)}")
            print(f"    {result['error']}")

    if ok:
        invalid = sum(1 for _, r in ok if not r["valid"])
        print(f"\nEstatísticas:")
        print(f"  Nodes extraídos:  {sum(r['nodes'] for _, r in ok)}")
        print(f"  Args extraídos:   {sum(r['args'] for _, r in ok)}")
        print(f"  JSONs guardados:  {len(ok)}  →  {OUTPUT_DIR}/")
        if invalid:
            print(f"  ⚠ Validação falhou em {invalid} ficheiro(s)")
        else:
            print(f"  ✓ Todos os ficheiros passaram a validação Layer 2")

    print()
    return 0 if not err else 1


if __name__ == "__main__":
    sys.exit(main())