"""
main.py — Layer 2

Ponto de entrada principal para extracção de arquitecturas ROS2.
Produz LaunchDescription Layer 2 conforme a especificação HAROS.

Uso:
  python3 main.py xml   <ficheiro.xml|pasta>
  python3 main.py yaml  <ficheiro.yaml|pasta>
  python3 main.py python <ficheiro.py|pasta>
  python3 main.py auto  <ficheiro>

Opções:
  --no-tree     Não mostra a parse tree
  --json        Output em JSON em vez de summary legível
  --json-file   Guarda o JSON em ficheiro (mesmo nome, extensão .json)
"""

import json
import os
import sys


EXTENSIONS = {
    'xml':    ['.launch.xml', '.xml'],
    'yaml':   ['.launch.yaml', '.launch.yml', '.yaml', '.yml'],
    'python': ['.launch.py', '.py'],
}


def get_parser(mode):
    if mode == 'xml':
        from parsers.xml.parser import XMLLaunchParser
        return XMLLaunchParser()
    elif mode == 'yaml':
        from parsers.yaml.parser import YAMLLaunchParser
        return YAMLLaunchParser()
    elif mode == 'python':
        from parsers.python.parser import PythonLaunchParser
        return PythonLaunchParser()
    return None


def detect_mode(file_path):
    for mode, exts in EXTENSIONS.items():
        for ext in exts:
            if file_path.endswith(ext):
                return mode
    return None


def collect_files(path, mode):
    if os.path.isfile(path):
        return [path]
    files = []
    exts = EXTENSIONS.get(mode, [])
    for root, _, filenames in os.walk(path):
        for f in sorted(filenames):
            for ext in exts:
                if f.endswith(ext):
                    files.append(os.path.join(root, f))
                    break
    return sorted(files)


def process_file(parser, file_path, show_tree=False, as_json=False, json_file=False):
    print(f"\n{'='*60}")
    print(f"  Ficheiro: {file_path}")
    print(f"{'='*60}")

    try:
        tree, ld = parser.parse(file_path)

        if show_tree:
            print("\n=== PARSE TREE ===\n")
            print(tree.pretty())

        # Sempre imprimir o summary no terminal
        ld.print_summary()

        # Sempre guardar o JSON em output/
        output_dir = "output"
        os.makedirs(output_dir, exist_ok=True)
        base_name = os.path.basename(file_path)
        json_path = os.path.join(output_dir, f"{base_name}.layer2.json")
        with open(json_path, "w", encoding="utf-8") as f:
            f.write(ld.to_json(indent=2))
        print(f"  [JSON guardado em: {json_path}]")

        # Se --json pedido, imprimir também no terminal
        if as_json:
            print()
            print(ld.to_json(indent=2))

        # Validação Layer 2
        try:
            from models.layer2 import Layer2Validator, IssueDetector
            errors = Layer2Validator().validate(ld)
            if errors:
                print(f"\n  [VALIDAÇÃO — {len(errors)} problema(s)]")
                for e in errors:
                    print(f"    {e}")
            else:
                print("  [VALIDAÇÃO sem erros]")

            # Issue Detection (Layer 6)
            issues = IssueDetector().detect(ld)
            if issues:
                print(f"\n  [ISSUES — {len(issues)} detectado(s)]")
                for issue in issues:
                    print(f"    [{issue.severity.upper():8s}] {issue.description}")
            else:
                print("  [ISSUES — nenhum detectado]")
        except Exception:
            pass

        return True, ld

    except Exception as e:
        print(f"\n[ERRO] {e}")
        import traceback
        traceback.print_exc()
        return False, None


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    mode = sys.argv[1].lower()
    path = sys.argv[2]
    show_tree  = '--tree' in sys.argv
    as_json    = '--json' in sys.argv or '--json-file' in sys.argv
    json_file  = '--json-file' in sys.argv

    if not os.path.exists(path):
        print(f"Erro: caminho não encontrado -> {path}")
        sys.exit(1)

    if mode == 'auto':
        if os.path.isfile(path):
            mode = detect_mode(path)
            if mode is None:
                print(f"Erro: formato não detectado para '{path}'")
                sys.exit(1)
        else:
            print("Erro: modo 'auto' só funciona com ficheiros, não pastas.")
            sys.exit(1)

    if mode not in ('xml', 'yaml', 'python'):
        print(f"Modo inválido: {mode}. Usa 'xml', 'yaml', 'python' ou 'auto'.")
        sys.exit(1)

    files = collect_files(path, mode)
    if not files:
        print(f"Nenhum ficheiro {mode} encontrado em '{path}'")
        sys.exit(1)

    # Com múltiplos ficheiros, desactivar tree e json por omissão
    if len(files) > 1:
        show_tree = '--tree' in sys.argv

    parser_obj = get_parser(mode)
    ok = 0
    errors = []

    for file_path in files:
        success, _ = process_file(
            parser_obj, file_path,
            show_tree=show_tree,
            as_json=as_json,
            json_file=json_file,
        )
        if success:
            ok += 1
        else:
            errors.append(file_path)

    if len(files) > 1:
        print(f"\n{'='*60}")
        print(f"  RESUMO: {ok}/{len(files)} ficheiros processados com sucesso")
        if errors:
            print(f"\n  Erros em:")
            for e in errors:
                print(f"    - {e}")
        print(f"{'='*60}\n")


if __name__ == "__main__":
    main()