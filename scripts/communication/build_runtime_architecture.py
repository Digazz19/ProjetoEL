#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from models.runtime_architecture import (
    Publication,
    QoSProfile,
    RuntimeArchitecture,
    RuntimeNode,
    Subscription,
    Topic,
)


def lit_value(value: Any) -> Optional[str]:
    """
    Converte LaunchSubstitution ou valores simples para string.
    Compatível com o formato JSON Layer 2.
    """
    if value is None:
        return None

    if isinstance(value, dict):
        t = value.get("type")

        if t == "literal":
            raw = value.get("value")
            return None if raw is None else str(raw)

        if t == "argument_reference":
            return f"$(arg {value.get('argument_name')})"

        if t == "environment_variable":
            name = value.get("variable_name")
            default = value.get("default_value")
            return f"$(env {name} {default})" if default is not None else f"$(env {name})"

        if t == "file_path":
            return f"$(find-pkg-share {value.get('package')})/{value.get('relative_path')}"

        if t == "expression":
            return json.dumps(value.get("expression"), ensure_ascii=False)

    return str(value)


def slug(value: str) -> str:
    value = value.strip()
    value = value.replace("/", "_")
    value = re.sub(r"[^a-zA-Z0-9_]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value or "root"


def topic_id(topic_name: str) -> str:
    return f"topic:{slug(topic_name)}"


def node_id_from_action(action_id: str) -> str:
    return f"runtime_node:{slug(action_id)}"


def endpoint_id(kind: str, node_id: str, topic_name: str) -> str:
    return f"{kind}:{slug(node_id)}:{slug(topic_name)}"


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def node_action_fields(action: dict) -> dict:
    return {
        "package": lit_value(action.get("package")),
        "executable": lit_value(action.get("executable")),
        "name": lit_value(action.get("name")),
        "namespace": lit_value(action.get("namespace")),
    }

def normalize_namespace(namespace: Optional[str]) -> str:
    """
    Normaliza namespace para forma absoluta sem trailing slash.
    Se for simbólico, não tenta aplicar porque depende de runtime.
    """
    if not namespace:
        return ""

    ns = str(namespace).strip()

    if not ns or ns == "/":
        return ""

    # Namespace simbólico, por exemplo $(arg namespace).
    # Não é seguro materializar topic names com isto.
    if "$(" in ns:
        return ""

    if not ns.startswith("/"):
        ns = "/" + ns

    return ns.rstrip("/")


def resolve_topic_name(topic_name: str, namespace: Optional[str] = None) -> str:
    """
    Resolve um nome de tópico para nome absoluto simples.

    - /scan fica /scan
    - scan fica /scan
    - scan com namespace /robot fica /robot/scan
    """
    topic = str(topic_name).strip()

    if not topic:
        return "/"

    if topic.startswith("/"):
        return "/" + topic.strip("/")

    ns = normalize_namespace(namespace)

    if ns:
        return f"{ns}/{topic.strip('/')}"

    return f"/{topic.strip('/')}"


def remap_from_to(remap: dict) -> tuple[Optional[str], Optional[str]]:
    """
    Extrai origem/destino de um remap Layer 2.
    Suporta vários nomes possíveis porque o JSON pode vir de parsers diferentes.
    """
    src = (
        remap.get("from")
        or remap.get("from_topic")
        or remap.get("src")
    )

    dst = (
        remap.get("to")
        or remap.get("to_topic")
        or remap.get("dst")
    )

    src_value = lit_value(src)
    dst_value = lit_value(dst)

    return src_value, dst_value


def get_node_remaps(action: dict) -> list[tuple[str, str]]:
    remaps = []

    for remap in action.get("remappings", []) or []:
        if not isinstance(remap, dict):
            continue

        src, dst = remap_from_to(remap)

        if src and dst:
            remaps.append((src, dst))

    return remaps


def topic_matches(interface_topic: str, remap_source: str) -> bool:
    """
    Verifica se um tópico da interface do node corresponde à origem do remap.

    Exemplo:
      /cmd_vel corresponde a cmd_vel
      cmd_vel corresponde a /cmd_vel
    """
    a = str(interface_topic).strip()
    b = str(remap_source).strip()

    if a == b:
        return True

    return resolve_topic_name(a) == resolve_topic_name(b)


def apply_remaps_to_topic(
    topic_name: str,
    action: dict,
    namespace: Optional[str],
) -> tuple[str, bool, Optional[str], Optional[str]]:
    """
    Aplica remaps do NodeAction ao tópico declarado na interface YAML.

    Retorna:
      final_topic, remap_applied, remap_source, remap_target
    """
    for src, dst in get_node_remaps(action):
        if topic_matches(topic_name, src):
            return resolve_topic_name(dst, namespace), True, src, dst

    return resolve_topic_name(topic_name, namespace), False, None, None


def resolve_endpoint_topic(
    architecture: RuntimeArchitecture,
    endpoint: dict,
    action: dict,
    namespace: Optional[str],
    runtime_name: str,
) -> dict:
    """
    Recebe um endpoint do YAML e devolve uma cópia com o tópico final
    após aplicação de remaps/namespaces do launch file.
    """
    if "topic" not in endpoint:
        architecture.warnings.append(
            f"Endpoint sem campo 'topic' no node {runtime_name}: {endpoint}"
        )
        return endpoint

    original_topic = endpoint["topic"]

    final_topic, applied, src, dst = apply_remaps_to_topic(
        original_topic,
        action,
        namespace,
    )

    resolved = dict(endpoint)
    resolved["topic"] = final_topic

    if applied:
        architecture.warnings.append(
            f"Remap aplicado no node {runtime_name}: {src} -> {dst} "
            f"(interface: {original_topic}, final: {final_topic})"
        )

    return resolved

def selector_matches(action: dict, selector: dict) -> bool:
    fields = node_action_fields(action)

    for key, expected in selector.items():
        if key == "action_id":
            continue

        actual = fields.get(key)

        if expected is not None and str(actual) != str(expected):
            return False

    return True


def find_node_action(layer2: dict, selector: dict) -> tuple[Optional[str], Optional[dict], list[str]]:
    actions = layer2.get("actions", {})

    if selector.get("action_id"):
        action_id = selector["action_id"]
        action = actions.get(action_id)

        if not action:
            return None, None, [f"action_id não encontrado: {action_id}"]

        if action.get("action_type") != "node":
            return None, None, [f"action_id não é NodeAction: {action_id}"]

        return action_id, action, []

    matches = []

    for action_id, action in actions.items():
        if action.get("action_type") != "node":
            continue

        if selector_matches(action, selector):
            matches.append((action_id, action))

    if len(matches) == 1:
        return matches[0][0], matches[0][1], []

    if len(matches) == 0:
        return None, None, [f"selector não encontrou nenhum NodeAction: {selector}"]

    return None, None, [f"selector ambíguo encontrou {len(matches)} NodeActions: {selector}"]


def ensure_topic(
    architecture: RuntimeArchitecture,
    name: str,
    msg_type: Optional[str],
) -> str:
    tid = topic_id(name)

    existing = architecture.topics.get(tid)

    if existing:
        if existing.msg_type is None and msg_type is not None:
            existing.msg_type = msg_type
        elif existing.msg_type and msg_type and existing.msg_type != msg_type:
            architecture.warnings.append(
                f"Topic {name} tem tipos diferentes nas anotações: "
                f"{existing.msg_type} vs {msg_type}"
            )

        return tid

    architecture.topics[tid] = Topic(
        id=tid,
        name=name,
        msg_type=msg_type,
    )

    return tid


def add_publication(
    architecture: RuntimeArchitecture,
    node_id: str,
    endpoint: dict,
) -> None:
    topic_name = endpoint["topic"]
    msg_type = endpoint.get("msg_type")
    qos = QoSProfile.from_dict(endpoint.get("qos"))

    tid = ensure_topic(architecture, topic_name, msg_type)
    pid = endpoint_id("publication", node_id, topic_name)

    architecture.publications[pid] = Publication(
        id=pid,
        node_id=node_id,
        topic_id=tid,
        topic_name=topic_name,
        msg_type=msg_type,
        qos=qos,
    )


def add_subscription(
    architecture: RuntimeArchitecture,
    node_id: str,
    endpoint: dict,
) -> None:
    topic_name = endpoint["topic"]
    msg_type = endpoint.get("msg_type")
    qos = QoSProfile.from_dict(endpoint.get("qos"))

    tid = ensure_topic(architecture, topic_name, msg_type)
    sid = endpoint_id("subscription", node_id, topic_name)

    architecture.subscriptions[sid] = Subscription(
        id=sid,
        node_id=node_id,
        topic_id=tid,
        topic_name=topic_name,
        msg_type=msg_type,
        qos=qos,
    )


def build_architecture(layer2_path: Path, node_interfaces_path: Path) -> RuntimeArchitecture:
    layer2 = load_json(layer2_path)
    node_interfaces = load_yaml(node_interfaces_path)

    architecture = RuntimeArchitecture(
        id=node_interfaces.get("architecture_id") or f"architecture:{layer2.get('launch_file_id')}",
        configuration_id=node_interfaces.get("configuration_id", "default"),
        source_layer2_path=str(layer2_path),
        source_launch_description_id=layer2.get("id"),
    )

    for node_ann in node_interfaces.get("nodes", []) or []:
        selector = node_ann.get("selector") or {}

        action_id, action, warnings = find_node_action(layer2, selector)

        architecture.warnings.extend(warnings)

        if not action_id or not action:
            continue

        fields = node_action_fields(action)

        runtime_name = (
            node_ann.get("runtime_name")
            or fields.get("name")
            or fields.get("executable")
            or action_id
        )

        namespace = node_ann.get("namespace", fields.get("namespace"))

        nid = node_id_from_action(action_id)

        architecture.nodes[nid] = RuntimeNode(
            id=nid,
            action_id=action_id,
            package=fields.get("package"),
            executable=fields.get("executable"),
            runtime_name=runtime_name,
            namespace=namespace,
            source_layer2_id=layer2.get("id"),
        )

        for pub in node_ann.get("publishes", []) or []:
            resolved_pub = resolve_endpoint_topic(
                architecture=architecture,
                endpoint=pub,
                action=action,
                namespace=namespace,
                runtime_name=runtime_name,
            )
            add_publication(architecture, nid, resolved_pub)

        for sub in node_ann.get("subscribes", []) or []:
            resolved_sub = resolve_endpoint_topic(
                architecture=architecture,
                endpoint=sub,
                action=action,
                namespace=namespace,
                runtime_name=runtime_name,
            )
            add_subscription(architecture, nid, resolved_sub)

    return architecture


def output_path_for(layer2_path: Path) -> Path:
    base = layer2_path.name

    if base.endswith(".layer2.json"):
        stem = base[:-len(".layer2.json")]
    else:
        stem = layer2_path.stem

    return Path("output") / "architecture" / f"{stem}.architecture.json"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Constrói uma arquitetura runtime a partir de Layer 2 JSON "
            "+ interfaces YAML dos nós individuais."
        )
    )
    parser.add_argument("layer2_json")
    parser.add_argument("node_interfaces_yaml")
    parser.add_argument(
        "-o",
        "--output",
        help="Caminho de output. Por omissão: output/architecture/<nome>.architecture.json",
    )

    args = parser.parse_args()

    layer2_path = Path(args.layer2_json)
    node_interfaces_path = Path(args.node_interfaces_yaml)

    if not layer2_path.exists():
        print(f"[ERRO] Layer 2 JSON não encontrado: {layer2_path}")
        return 1

    if not node_interfaces_path.exists():
        print(f"[ERRO] Interface YAML dos nós não encontrada: {node_interfaces_path}")
        return 1

    architecture = build_architecture(layer2_path, node_interfaces_path)

    output_path = Path(args.output) if args.output else output_path_for(layer2_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(architecture.to_dict(), f, indent=2, ensure_ascii=False)

    print(f"[OK] Arquitetura gerada: {output_path}")
    print(f"[OK] Nodes: {len(architecture.nodes)}")
    print(f"[OK] Topics: {len(architecture.topics)}")
    print(f"[OK] Publications: {len(architecture.publications)}")
    print(f"[OK] Subscriptions: {len(architecture.subscriptions)}")

    if architecture.warnings:
        print(f"[AVISO] Warnings: {len(architecture.warnings)}")
        for warning in architecture.warnings:
            print(f"  - {warning}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())