#!/usr/bin/env python3
"""
export_haros2viz.py — Exporta um model.json no formato esperado pelo visualizador HAROS2.

Agrega:
  - JSON Layer 2 (launch_descriptions)
  - Ficheiros Layer 1 anotados (node_implementations)
  - Issues estruturais e de comunicação (issues)

Uso:
  python3 scripts/export_haros2viz.py \
    output/robot.launch.layer2.json \
    --layer1 node_interfaces/robot.layer1.yaml \
    --issues output/issues/robot.launch.issues.json \
    --issues output/issues/robot.launch.communication.issues.json \
    --output output/robot.model.json

  # Ou em modo automático (agrega tudo em output/)
  python3 scripts/export_haros2viz.py --auto output/
"""

import json
import os
import sys
import argparse
import datetime
import yaml


# ---------------------------------------------------------------------------
# Converters
# ---------------------------------------------------------------------------

def load_layer2_json(path: str) -> dict:
    """Carrega um JSON Layer 2 gerado pelo ProjetoEL."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_layer1_yaml(path: str) -> list:
    """
    Carrega um ficheiro .layer1.yaml e converte para o formato
    node_implementations esperado pelo visualizador HAROS2.
    """
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    implementations = []
    for node in data.get("node_implementations", []):
        impl = {
            "id": node["id"],
            "package": node.get("package", ""),
            "executable": node.get("executable", ""),
            "node_type": node.get("node_type", "standard"),
            "language": node.get("language", "unknown"),
            "publishers": [],
            "subscriptions": [],
            "service_servers": [],
            "service_clients": [],
            "action_servers": [],
            "action_clients": [],
            "timers": [],
            "parameters": [],
            "provenance": node.get("provenance", {
                "extraction_method": "annotation",
                "confidence": 0.8
            }),
        }

        # Publishers
        for pub in node.get("publishers", []):
            impl["publishers"].append({
                "id": pub["id"],
                "topic": pub.get("topic_name", ""),
                "message_type": pub.get("message_type", ""),
                "qos_profile": pub.get("qos_profile", {}),
                "provenance": pub.get("provenance", {"extraction_method": "annotation", "confidence": 0.8}),
            })

        # Subscriptions
        for sub in node.get("subscriptions", []):
            impl["subscriptions"].append({
                "id": sub["id"],
                "topic": sub.get("topic_name", ""),
                "message_type": sub.get("message_type", ""),
                "qos_profile": sub.get("qos_profile", {}),
                "provenance": sub.get("provenance", {"extraction_method": "annotation", "confidence": 0.8}),
            })

        implementations.append(impl)

    return implementations


def load_issues_json(path: str) -> list:
    """Carrega um JSON de issues gerado pelo ProjetoEL."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    # Suporta lista directa ou wrapper {"issues": [...]}
    if isinstance(data, list):
        return data
    return data.get("issues", [])



# ---------------------------------------------------------------------------
# Workspace builder
# ---------------------------------------------------------------------------

def extract_packages_from_layer2(ld: dict) -> dict:
    """
    Extrai packages únicos de um LaunchDescription Layer 2.
    Retorna {package_name: [list_of_node_executables]}
    """
    packages = {}
    for aid, action in ld.get("actions", {}).items():
        if action.get("action_type") == "node":
            pkg_field = action.get("package", {})
            if isinstance(pkg_field, dict) and pkg_field.get("type") == "literal":
                pkg = pkg_field.get("value", "")
            elif isinstance(pkg_field, str):
                pkg = pkg_field
            else:
                continue
            if pkg:
                exe_field = action.get("executable", {})
                if isinstance(exe_field, dict):
                    exe = exe_field.get("value", "")
                else:
                    exe = str(exe_field)
                packages.setdefault(pkg, set()).add(exe)
    return {k: sorted(v) for k, v in packages.items()}


def build_workspaces(
    layer2_jsons: list,
    layer1_yamls: list,
    node_implementations: list,
) -> list:
    """
    Constrói a lista de workspaces para o visualizador HAROS2.
    Agrupa packages por nome, associa ficheiros launch e node implementations.

    O visualizador HAROS2 conta:
    - NODES:   node_implementations na raiz com package == pkg_name
    - LAUNCHES: launch_descriptions com launch_file_id que começa com pkg_name/
    """
    import hashlib

    # 1. Recolher todos os packages de todos os layer2
    # e normalizar o launch_file_id para incluir o package como prefixo
    all_packages = {}   # {pkg_name: {"files": set(), "launch_ids": set()}}
    ld_updates = {}     # {ld_id: new_launch_file_id} para actualizar depois

    for path in layer2_jsons:
        ld = load_layer2_json(path)
        pkgs = extract_packages_from_layer2(ld)
        launch_file_path = ld.get("launch_file_id", os.path.basename(path))

        for pkg_name, executables in pkgs.items():
            if pkg_name not in all_packages:
                all_packages[pkg_name] = {"files": set(), "launch_ids": set()}
            all_packages[pkg_name]["files"].add(launch_file_path)
            all_packages[pkg_name]["launch_ids"].add(ld.get("id", ""))

    # 2. Construir a lista de packages
    packages = []
    for pkg_name, pkg_data in sorted(all_packages.items()):
        pkg_id = f"package_{pkg_name.replace('-', '_').replace('.', '_')}"

        # Ficheiros do package (os launch files que referenciam este package)
        files = []
        for fpath in sorted(pkg_data["files"]):
            files.append({
                "id": f"file_{hashlib.md5(fpath.encode()).hexdigest()[:8]}",
                "path": fpath,
                "language": "python" if fpath.endswith(".py") else
                            "xml" if fpath.endswith(".xml") else "yaml",
                "provenance": {
                    "extraction_method": "static_analysis",
                    "confidence": 1.0
                }
            })

        pkg_entry = {
            "id": pkg_id,
            "name": pkg_name,
            "path": f"src/{pkg_name}",
            "files": files,
            "provenance": {
                "extraction_method": "static_analysis",
                "confidence": 1.0
            }
        }
        packages.append(pkg_entry)

    if not packages:
        return []

    return [{
        "id": "workspace_projetoel",
        "name": "ProjetoEL Workspace",
        "path": "/workspace/ProjetoEL",
        "ros_distro": "humble",
        "packages": packages,
        "provenance": {
            "extraction_method": "static_analysis",
            "confidence": 1.0
        }
    }]

# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------

def build_model(
    layer2_jsons: list,
    layer1_yamls: list,
    issues_jsons: list,
    project_name: str = "ProjetoEL",
) -> dict:
    """Constrói o model.json no formato HAROS2."""

    # Agregar launch_descriptions
    # Normalizar launch_file_id para pkg_name/filename.py (esperado pelo visualizador)
    launch_descriptions = []
    for path in layer2_jsons:
        ld = load_layer2_json(path)
        if "id" not in ld:
            ld["id"] = f"launch_{os.path.basename(path).replace('.json', '')}"
        # Se launch_file_id não tem separador de pasta, tentar inferir o package
        lfi = ld.get("launch_file_id", "")
        if lfi and "/" not in lfi:
            # Extrair package principal dos nodes
            pkgs = extract_packages_from_layer2(ld)
            if pkgs:
                main_pkg = sorted(pkgs.items(), key=lambda x: len(x[1]), reverse=True)[0][0]
                ld["launch_file_id"] = f"{main_pkg}/{lfi}"
        launch_descriptions.append(ld)

    # Agregar node_implementations
    node_implementations = []
    for path in layer1_yamls:
        impls = load_layer1_yaml(path)
        node_implementations.extend(impls)

    # Agregar issues
    issues = []
    for path in issues_jsons:
        issues.extend(load_issues_json(path))

    # Construir modelo completo
    # Construir workspaces
    workspaces = build_workspaces(layer2_jsons, layer1_yamls, node_implementations)

    model = {
        "metamodel_version": "1.0.0",
        "project_name": project_name,
        "extraction_timestamp": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "workspaces": workspaces,
        "node_implementations": node_implementations,
        "launch_descriptions": launch_descriptions,
        "execution_configurations": [
            {
                "id": f"exec_config_{i+1}",
                "name": os.path.basename(path).replace(".layer2.json", ""),
                "description": f"Launch {os.path.basename(path).replace('.layer2.json', '')}",
                "execution_commands": [
                    {
                        "type": "launch",
                        "launch_file": ld.get("launch_file_id", "")
                    }
                ]
            }
            for i, (path, ld) in enumerate(zip(layer2_jsons, launch_descriptions))
        ],
        "runtime": {
            "nodes": [],
            "publications": [],
            "subscriptions": [],
            "timers": [],
            "parameters": [],
            "topics": [],
        },
        "issues": issues,
        "metrics": [],
        "verification_results": [],
    }

    return model


# ---------------------------------------------------------------------------
# Auto mode — agrega todos os ficheiros em output/
# ---------------------------------------------------------------------------

def auto_build(output_dir: str, project_name: str = "ProjetoEL") -> dict:
    """
    Modo automático: agrega todos os JSONs Layer 2, YAMLs Layer 1
    e JSONs de issues encontrados nas pastas padrão.
    """
    layer2_jsons = []
    layer1_yamls = []
    issues_jsons = []

    # Encontrar JSONs Layer 2 em output/ (excluindo subpastas)
    for fname in sorted(os.listdir(output_dir)):
        if fname.endswith(".layer2.json"):
            layer2_jsons.append(os.path.join(output_dir, fname))

    # Encontrar YAMLs Layer 1 em node_interfaces/
    ni_dir = os.path.join(os.path.dirname(output_dir), "node_interfaces")
    if os.path.isdir(ni_dir):
        for fname in sorted(os.listdir(ni_dir)):
            if fname.endswith(".layer1.yaml"):
                layer1_yamls.append(os.path.join(ni_dir, fname))

    # Encontrar JSONs de issues em output/issues/
    issues_dir = os.path.join(output_dir, "issues")
    if os.path.isdir(issues_dir):
        for fname in sorted(os.listdir(issues_dir)):
            if fname.endswith(".json"):
                issues_jsons.append(os.path.join(issues_dir, fname))

    print(f"  Layer 2 JSONs encontrados:  {len(layer2_jsons)}")
    print(f"  Layer 1 YAMLs encontrados:  {len(layer1_yamls)}")
    print(f"  Issues JSONs encontrados:   {len(issues_jsons)}")

    return build_model(layer2_jsons, layer1_yamls, issues_jsons, project_name)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Exporta model.json no formato HAROS2 para o visualizador."
    )
    parser.add_argument(
        "layer2",
        nargs="?",
        help="JSON Layer 2 a incluir (pode ser repetido). Em modo --auto, pasta output/."
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Modo automático: agrega tudo em output/ e node_interfaces/"
    )
    parser.add_argument(
        "--layer1",
        action="append",
        default=[],
        metavar="YAML",
        help="Ficheiro .layer1.yaml (pode ser repetido)"
    )
    parser.add_argument(
        "--issues",
        action="append",
        default=[],
        metavar="JSON",
        help="Ficheiro de issues JSON (pode ser repetido)"
    )
    parser.add_argument(
        "--output", "-o",
        default="output/model.json",
        help="Caminho do ficheiro de saída (default: output/model.json)"
    )
    parser.add_argument(
        "--project",
        default="ProjetoEL",
        help="Nome do projecto (default: ProjetoEL)"
    )

    args = parser.parse_args()

    if args.auto:
        output_dir = args.layer2 or "output"
        print(f"\nModo automático — pasta: {output_dir}")
        model = auto_build(output_dir, args.project)
        # Adicionar layer1 YAMLs passados explicitamente
        if args.layer1:
            extra_impls = []
            for yaml_path in args.layer1:
                try:
                    extra_impls.extend(load_layer1_yaml(yaml_path))
                except Exception as e:
                    print(f"  [AVISO] Erro ao ler {yaml_path}: {e}")
            if extra_impls:
                model["node_implementations"].extend(extra_impls)
                # Actualizar workspaces com os novos node_implementations
                if model["workspaces"]:
                    model["workspaces"] = build_workspaces(
                        [os.path.join(output_dir, f)
                         for f in os.listdir(output_dir)
                         if f.endswith(".layer2.json")],
                        args.layer1,
                        model["node_implementations"],
                    )
                print(f"  Layer 1 extras carregados: {len(extra_impls)} node_implementations")
    elif args.layer2:
        layer2_files = [args.layer2]
        model = build_model(layer2_files, args.layer1, args.issues, args.project)
    else:
        parser.print_help()
        sys.exit(1)

    # Garantir que a pasta de output existe
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)

    # Guardar
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(model, f, indent=2, ensure_ascii=False)

    print(f"\n  [OK] model.json guardado em: {args.output}")
    print(f"       launch_descriptions: {len(model['launch_descriptions'])}")
    print(f"       node_implementations: {len(model['node_implementations'])}")
    print(f"       issues: {len(model['issues'])}")
    print(f"\n  Abre o visualizador em:")
    print(f"  https://haros-framework.github.io/haros2viz/")
    print(f"  e carrega o ficheiro: {args.output}")


if __name__ == "__main__":
    main()