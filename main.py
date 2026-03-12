import os
import sys

from parsers.xml.parser import XMLLaunchParser
from parsers.yaml.parser import YAMLLaunchParser
from parsers.python.parser import PythonLaunchParser


def print_architecture(architecture, name=""):
    print(f"\n=== ARQUITETURA EXTRAÍDA ({name}) ===\n")

    if architecture.nodes:
        for i, node in enumerate(architecture.nodes, start=1):
            print(f"[NODE {i}]")
            print(node)
            print()
    else:
        print("Sem nodes extraídos.\n")

    print("ARGS:", architecture.args)
    print("LETS:", architecture.lets)
    print("INCLUDES:", architecture.includes)
    print("ENV:", architecture.env)
    print("UNSET_ENV:", architecture.unset_env)
    print("EXECUTABLES:", architecture.executables)


def main():
    if len(sys.argv) < 3:
        print("Uso:")
        print("  python3 main.py xml examples/test.xml")
        print("  python3 main.py yaml examples/test.yaml")
        print("  python3 main.py python examples/test_launch.py")
        sys.exit(1)

    mode = sys.argv[1].lower()
    file_path = sys.argv[2]

    if not os.path.exists(file_path):
        print(f"Erro: ficheiro não encontrado -> {file_path}")
        sys.exit(1)

    if mode == "xml":
        parser = XMLLaunchParser()
    elif mode == "yaml":
        parser = YAMLLaunchParser()
    elif mode == "python":
        parser = PythonLaunchParser()
    else:
        print(f"Modo inválido: {mode}")
        print("Usa 'xml', 'yaml' ou 'python'.")
        sys.exit(1)

    tree, architecture = parser.parse(file_path)

    print("\n=== PARSE TREE ===\n")
    print(tree.pretty())

    print_architecture(architecture, mode.upper())


if __name__ == "__main__":
    main()