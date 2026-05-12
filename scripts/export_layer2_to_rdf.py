#!/usr/bin/env python3

import json
import sys
from pathlib import Path
from urllib.parse import quote

from rdflib import Graph, Namespace, URIRef, Literal, RDF, RDFS, XSD


ROS = Namespace("http://example.org/ros-launch#")
RES = Namespace("http://example.org/ros-launch/resource/")


ACTION_TYPE_CLASS = {
    "declare_argument": ROS.DeclareArgumentAction,
    "set_parameter": ROS.SetParameterAction,
    "push_namespace": ROS.PushNamespaceAction,
    "node": ROS.NodeAction,
    "include": ROS.IncludeAction,
    "group": ROS.GroupAction,
}


def uri(kind: str, raw: str) -> URIRef:
    return URIRef(f"{RES}{kind}/{quote(str(raw), safe='')}")


def lit_value(sub):
    if sub is None:
        return None

    if isinstance(sub, dict):
        t = sub.get("type")

        if t == "literal":
            return sub.get("value")

        if t == "argument_reference":
            return f"$(arg {sub.get('argument_name')})"

        if t == "environment_variable":
            name = sub.get("variable_name")
            default = sub.get("default_value")
            return f"$(env {name} {default})" if default is not None else f"$(env {name})"

        if t == "file_path":
            return f"$(find-pkg-share {sub.get('package')})/{sub.get('relative_path')}"

        if t == "expression":
            return json.dumps(sub.get("expression"), ensure_ascii=False)

    return str(sub)


def add_parameter(g, owner_uri, owner_id, name, value):
    param_uri = uri("parameter", f"{owner_id}:param:{name}")
    g.add((param_uri, RDF.type, ROS.Parameter))
    g.add((owner_uri, ROS.hasParameter, param_uri))
    g.add((param_uri, ROS.hasParameterName, Literal(str(name))))

    resolved = lit_value(value)
    if resolved is not None:
        g.add((param_uri, ROS.hasParameterValue, Literal(str(resolved))))


def add_provenance(g, action_uri, action):
    prov = action.get("provenance")
    if not isinstance(prov, dict):
        return

    prov_uri = uri("provenance", action.get("id", "") + ":provenance")
    g.add((prov_uri, RDF.type, ROS.Provenance))
    g.add((action_uri, ROS.hasProvenance, prov_uri))

    source = prov.get("source_location", {})
    if isinstance(source, dict):
        source_file = source.get("file_path") or source.get("file")

        if source_file:
            g.add((prov_uri, ROS.hasSourceFile, Literal(source_file)))

    if prov.get("confidence") is not None:
        g.add((prov_uri, ROS.hasConfidence, Literal(float(prov["confidence"]), datatype=XSD.decimal)))


def add_condition(g, action_uri, action):
    for idx, cond in enumerate(action.get("conditions", []) or []):
        cond_uri = uri("condition", f"{action.get('id')}:condition:{idx}")
        g.add((cond_uri, RDF.type, ROS.Condition))
        g.add((action_uri, ROS.hasCondition, cond_uri))
        g.add((cond_uri, ROS.hasConditionExpression, Literal(json.dumps(cond, ensure_ascii=False))))


def add_remappings(g, action_uri, action):
    for idx, remap in enumerate(action.get("remappings", []) or []):
        remap_uri = uri("remapping", f"{action.get('id')}:remap:{idx}")
        g.add((remap_uri, RDF.type, ROS.Remapping))
        g.add((action_uri, ROS.hasRemapping, remap_uri))

        src = remap.get("from") or remap.get("from_topic") or remap.get("src")
        dst = remap.get("to") or remap.get("to_topic") or remap.get("dst")

        if src is not None:
            g.add((remap_uri, ROS.remapFrom, Literal(str(src))))

        dst_value = lit_value(dst)
        if dst_value is not None:
            g.add((remap_uri, ROS.remapTo, Literal(str(dst_value))))


def add_action_specific_triples(g, action_uri, action):
    action_type = action.get("action_type")

    if action_type == "node":
        package = lit_value(action.get("package"))
        executable = lit_value(action.get("executable"))
        name = lit_value(action.get("name"))
        namespace = lit_value(action.get("namespace"))

        if package is not None:
            g.add((action_uri, ROS.hasPackage, Literal(str(package))))
        if executable is not None:
            g.add((action_uri, ROS.hasExecutable, Literal(str(executable))))
        if name is not None:
            g.add((action_uri, ROS.hasNodeName, Literal(str(name))))
        if namespace is not None:
            g.add((action_uri, ROS.hasNamespace, Literal(str(namespace))))

        for pname, pvalue in (action.get("parameters") or {}).items():
            add_parameter(g, action_uri, action["id"], pname, pvalue)

        add_remappings(g, action_uri, action)

    elif action_type == "declare_argument":
        if action.get("name") is not None:
            g.add((action_uri, ROS.hasArgumentName, Literal(str(action["name"]))))

        default_value = lit_value(action.get("default_value"))
        if default_value is not None:
            g.add((action_uri, ROS.hasDefaultValue, Literal(str(default_value))))

    elif action_type == "set_parameter":
        add_parameter(g, action_uri, action["id"], action.get("name", ""), action.get("value"))

        if action.get("target_scope") is not None:
            g.add((action_uri, ROS.hasTargetScope, Literal(str(action["target_scope"]))))

    elif action_type == "push_namespace":
        namespace = lit_value(action.get("namespace"))
        if namespace is not None:
            g.add((action_uri, ROS.hasNamespace, Literal(str(namespace))))

    elif action_type == "include":
        included = action.get("included_launch_id")
        if included:
            g.add((action_uri, ROS.includesLaunch, uri("launch", included)))

        for arg_name, arg_value in (action.get("argument_mappings") or {}).items():
            add_parameter(g, action_uri, action["id"], arg_name, arg_value)

    elif action_type == "group":
        namespace = lit_value(action.get("namespace"))
        if namespace is not None:
            g.add((action_uri, ROS.hasNamespace, Literal(str(namespace))))

        for pname, pvalue in (action.get("set_parameters") or {}).items():
            add_parameter(g, action_uri, action["id"], pname, pvalue)


def layer2_json_to_graph(data: dict) -> Graph:
    g = Graph()
    g.bind("ros", ROS)
    g.bind("res", RES)

    launch_uri = uri("launch", data["id"])

    g.add((launch_uri, RDF.type, ROS.LaunchDescription))
    g.add((launch_uri, RDFS.label, Literal(data["id"])))
    g.add((launch_uri, ROS.hasLaunchFileId, Literal(data.get("launch_file_id", ""))))
    g.add((launch_uri, ROS.hasFormat, Literal(data.get("format", ""))))

    actions = data.get("actions", {})

    for action_id, action in actions.items():
        action_uri = uri("action", action_id)
        cls = ACTION_TYPE_CLASS.get(action.get("action_type"), ROS.LaunchAction)

        g.add((action_uri, RDF.type, ROS.LaunchAction))
        g.add((action_uri, RDF.type, cls))
        g.add((action_uri, RDFS.label, Literal(action_id)))
        g.add((action_uri, ROS.hasActionId, Literal(action_id)))
        g.add((launch_uri, ROS.hasAction, action_uri))

        add_provenance(g, action_uri, action)
        add_condition(g, action_uri, action)
        add_action_specific_triples(g, action_uri, action)

    for action_id in data.get("launch_sequence", []) or []:
        g.add((launch_uri, ROS.hasTopLevelAction, uri("action", action_id)))

    for action in actions.values():
        parent_uri = uri("action", action["id"])
        for child_id in action.get("children", []) or []:
            g.add((parent_uri, ROS.hasChildAction, uri("action", child_id)))

    return g


def main():
    if len(sys.argv) < 2:
        print("uso:")
        print("  python3 scripts/export_layer2_to_rdf.py input.layer2.json [output.layer2.ttl]")
        return 2

    input_path = Path(sys.argv[1])

    if not input_path.exists():
        print(f"[ERRO] JSON Layer 2 não encontrado: {input_path}")
        return 1

    if len(sys.argv) >= 3:
        output_path = Path(sys.argv[2])
    else:
        output_dir = Path("output/rdf")
        output_path = output_dir / f"{input_path.stem}.ttl"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with input_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    g = layer2_json_to_graph(data)
    g.serialize(destination=str(output_path), format="turtle")

    print(f"[OK] RDF gerado: {output_path}")
    print(f"[OK] triples: {len(g)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())