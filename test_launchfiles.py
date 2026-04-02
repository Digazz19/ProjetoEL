"""
test_python_launches.py

Testa o parser Python em todos os launch files .py encontrados
nas pastas indicadas, e mostra um resumo detalhado dos resultados.

Uso:
    python3 test_python_launches.py
    python3 test_python_launches.py examples/real-python
    python3 test_python_launches.py examples/real-python examples/outro
"""

import sys
import os

# ---------------------------------------------------------------------------
# Configuração — pastas a pesquisar (podes adicionar mais)
# ---------------------------------------------------------------------------

DEFAULT_DIRS = [
    "examples/real-python",
]

# ---------------------------------------------------------------------------
# Setup do parser
# ---------------------------------------------------------------------------

def build_parser():
    from parsers.python.parser import PythonLaunchParser
    return PythonLaunchParser()


def build_transformer():
    return None  # transformer já está encapsulado no PythonLaunchParser


# ---------------------------------------------------------------------------
# Descobrir ficheiros
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Testar um ficheiro
# ---------------------------------------------------------------------------

def test_file(parser, TransformerClass, path):
    try:
        tree, arch = parser.parse(path)

        return {
            "status": "OK",
            "nodes": len(arch.nodes),
            "topics": len(arch.topics),
            "args": len(arch.args),
            "includes": len(arch.includes),
            "error": None,
        }

    except Exception as e:
        # Extrair a mensagem mais útil do erro
        msg = str(e)
        # Tentar extrair linha e coluna se disponível
        import re
        m = re.search(r"line (\d+)[^\n]*col(?:umn)? (\d+)", msg)
        location = f" (linha {m.group(1)}, col {m.group(2)})" if m else ""

        # Pegar só a primeira linha da mensagem
        short_msg = msg.split("\n")[0][:100]

        return {
            "status": "ERRO",
            "nodes": 0,
            "topics": 0,
            "args": 0,
            "includes": 0,
            "error": short_msg + location,
        }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    dirs = sys.argv[1:] if len(sys.argv) > 1 else DEFAULT_DIRS

    print(f"\n{'='*70}")
    print(f"  Teste do Parser Python — Launch Files")
    print(f"  Pastas: {', '.join(dirs)}")
    print(f"{'='*70}\n")

    # Construir parser
    try:
        parser = build_parser()
        TransformerClass = build_transformer()
    except Exception as e:
        print(f"[ERRO] Não foi possível inicializar o parser: {e}")
        sys.exit(1)

    # Descobrir ficheiros
    files = find_launch_files(dirs)
    if not files:
        print("Nenhum launch file Python encontrado nas pastas indicadas.")
        sys.exit(0)

    print(f"Ficheiros encontrados: {len(files)}\n")

    # Testar cada ficheiro
    results = []
    for path in files:
        result = test_file(parser, None, path)
        results.append((path, result))

        status = result["status"]
        name = os.path.relpath(path)

        if status == "OK":
            print(f"  ✓  {name}")
            print(f"       nodes={result['nodes']}  tópicos={result['topics']}  "
                  f"args={result['args']}  includes={result['includes']}")
        else:
            print(f"  ✗  {name}")
            print(f"       {result['error']}")

    # Resumo
    ok = [r for _, r in results if r["status"] == "OK"]
    err = [r for _, r in results if r["status"] == "ERRO"]

    print(f"\n{'='*70}")
    print(f"  RESULTADO: {len(ok)}/{len(results)} ficheiros OK")
    print(f"{'='*70}")

    if err:
        print(f"\nFicheiros com erro ({len(err)}):")
        for path, result in results:
            if result["status"] == "ERRO":
                print(f"  - {os.path.relpath(path)}")
                print(f"    {result['error']}")

    # Estatísticas globais dos OK
    if ok:
        total_nodes = sum(r["nodes"] for r in ok)
        total_topics = sum(r["topics"] for r in ok)
        print(f"\nEstatísticas (ficheiros OK):")
        print(f"  Total nodes extraídos:   {total_nodes}")
        print(f"  Total tópicos extraídos: {total_topics}")

    print()
    return 0 if not err else 1


if __name__ == "__main__":
    sys.exit(main())