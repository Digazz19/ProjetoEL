"""
transformerXML.py — Layer 2

Transformer Lark para launch files XML.
Produz um LaunchDescription Layer 2 conforme a especificação HAROS.
"""

from lark import Transformer
import re as _re

from models.layer2 import (
    LaunchDescription,
    LaunchSubstitution,
    ElementProvenance,
    SourceRef,
    ActionIDGenerator,
    DeclareArgumentAction,
    SetParameterAction,
    PushNamespaceAction,
    NodeAction,
    IncludeAction,
    GroupAction,
    Remapping,
    ActionType,
)

def _parse_launch_condition_to_ir(condition_str: str):
    s = str(condition_str).strip()

    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        s = s[1:-1].strip()

    parts = _re.split(r"\s+or\s+", s)
    if len(parts) > 1:
        result = _parse_launch_condition_to_ir(parts[0])
        for p in parts[1:]:
            result = ["or", result, _parse_launch_condition_to_ir(p)]
        return result

    parts = _re.split(r"\s+and\s+", s)
    if len(parts) > 1:
        result = _parse_launch_condition_to_ir(parts[0])
        for p in parts[1:]:
            result = ["and", result, _parse_launch_condition_to_ir(p)]
        return result

    m = _re.match(r"^not\s+(.+)$", s)
    if m:
        return ["not", _parse_launch_condition_to_ir(m.group(1))]

    m = _re.match(r"^\$\(var\s+([A-Za-z_][A-Za-z0-9_]*)\)$", s)
    if m:
        return ["eq", ["launch_arg_get", m.group(1)], "true"]

    m = _re.match(r"^\$\(arg\s+([A-Za-z_][A-Za-z0-9_]*)\)$", s)
    if m:
        return ["eq", ["launch_arg_get", m.group(1)], "true"]

    m = _re.match(r"^\$\(env\s+([A-Za-z_][A-Za-z0-9_]*)\)$", s)
    if m:
        return ["truthy", ["env_get", m.group(1)]]

    return ["truthy", ["var_get", s]]
class LaunchXMLTransformer(Transformer):

    def __init__(self, file_path: str = "unknown.launch.xml"):
        super().__init__()
        self._file_path = file_path
        self._file_id = ActionIDGenerator.file_id_from_path(file_path)
        self._id_gen = ActionIDGenerator(self._file_id)

    def _provenance(self, confidence: float = 1.0) -> ElementProvenance:
        return ElementProvenance(
            extraction_method="static_analysis",
            source_location=SourceRef(file_path=self._file_path),
            confidence=confidence,
        )

    def _sub(self, value) -> LaunchSubstitution:
        import re
        if isinstance(value, LaunchSubstitution):
            return value
        if value is None:
            return LaunchSubstitution.literal(None)
        s = str(value)
        m = re.match(r'^\$\((var|arg)\s+(\S+)\)$', s)
        if m:
            return LaunchSubstitution.argument_reference(m.group(2))
        m = re.match(r'^\$\(env\s+(\S+)(?:\s+(.+))?\)$', s)
        if m:
            return LaunchSubstitution.environment_variable(m.group(1), m.group(2))
        m = re.match(r'^\$\(find-pkg-share\s+(\S+)\)/(.+)$', s)
        if m:
            return LaunchSubstitution.file_path(m.group(1), m.group(2))
        return LaunchSubstitution.literal(s)

    def _conditions_for_item(self, item, inherited=None):
        cond_list = list(inherited or [])

        if not isinstance(item, dict):
            return cond_list

        if item.get("if"):
            cond_list.append(_parse_launch_condition_to_ir(item["if"]))

        if item.get("unless"):
            cond_list.append(["not", _parse_launch_condition_to_ir(item["unless"])])

        return cond_list

    def start(self, items):
        return items[0]

    def launch(self, items):
        ld_id = f"launch_desc_{self._file_id}"
        ld = LaunchDescription(
            id=ld_id,
            launch_file_id=self._file_id,
            format="xml",
            provenance=ElementProvenance(
                extraction_method="static_analysis",
                source_location=SourceRef(file_path=self._file_path),
                confidence=0.95,
            ),
        )
        for item in items:
            self._process_item(ld, item)
        return ld

    def _process_item(self, ld, item, conditions=None):
        if item is None:
            return

        if isinstance(item, list):
            for sub in item:
                self._process_item(ld, sub, conditions)
            return

        if not isinstance(item, dict):
            return

        t = item.get("type")
        item_conditions = self._conditions_for_item(item, conditions)

        if t == "node":
            ld.add_action(self._make_node_action(item, item_conditions))

        elif t == "arg":
            ld.add_action(DeclareArgumentAction(
                id=self._id_gen.generate(f"arg_{item.get('name','')}"),
                action_type=ActionType.DECLARE_ARGUMENT,
                name=item.get("name", ""),
                default_value=self._sub(item.get("default")) if item.get("default") is not None else None,
                description=item.get("description"),
                conditions=item_conditions,
                provenance=self._provenance(0.9 if item_conditions else 1.0),
            ))

        elif t == "let":
            ld.add_action(SetParameterAction(
                id=self._id_gen.generate(f"let_{item.get('name','')}"),
                action_type=ActionType.SET_PARAMETER,
                name=item.get("name", ""),
                value=self._sub(item.get("value")),
                target_scope="local",
                conditions=item_conditions,
                provenance=self._provenance(0.9 if item_conditions else 1.0),
            ))

        elif t == "set_env":
            ld.add_action(SetParameterAction(
                id=self._id_gen.generate(f"set_env_{item.get('name','')}"),
                action_type=ActionType.SET_PARAMETER,
                name=item.get("name", ""),
                value=self._sub(item.get("value")),
                target_scope="global",
                conditions=item_conditions,
                provenance=self._provenance(0.9 if item_conditions else 1.0),
            ))

        elif t == "set_parameter":
            name = item.get("name", "")
            value = item.get("value")

            action = SetParameterAction(
                id=self._id_gen.generate(f"set_param_{name}"),
                action_type=ActionType.SET_PARAMETER,
                name=str(name) if name else "",
                value=self._sub(value),
                target_scope=item.get("target_scope", "local"),
                conditions=item_conditions,
                provenance=self._provenance(0.9 if item_conditions else 1.0),
            )
            ld.add_action(action)

        elif t == "include":
            included_id = ActionIDGenerator.file_id_from_path(item.get("file") or "unknown")
            arg_mappings = {
                arg["name"]: self._sub(arg.get("value") or arg.get("default"))
                for arg in item.get("args", [])
                if isinstance(arg, dict) and arg.get("name")
            }

            ld.add_action(IncludeAction(
                id=self._id_gen.generate(f"include_{included_id}"),
                action_type=ActionType.INCLUDE,
                included_launch_id=f"launch_desc_{included_id}",
                argument_mappings=arg_mappings,
                conditions=item_conditions,
                provenance=self._provenance(0.9 if item_conditions else 1.0),
            ))

        elif t == "push_namespace":
            ns = item.get("namespace")
            action = PushNamespaceAction(
                id=self._id_gen.generate(f"push_ns_{ns}"),
                action_type=ActionType.PUSH_NAMESPACE,
                namespace=self._sub(ns) if ns else None,
                conditions=item_conditions,
                provenance=self._provenance(0.9 if item_conditions else 1.0),
            )
            ld.add_action(action)

        elif t == "group":
            group_id = self._id_gen.generate("group")
            group = GroupAction(
                id=group_id,
                action_type=ActionType.GROUP,
                namespace=self._sub(item.get("namespace")) if item.get("namespace") else None,
                conditions=item_conditions,
                provenance=self._provenance(0.9 if item_conditions else 1.0),
            )
            ld.add_action(group)

            child_ids = []
            for child in item.get("children", []):
                prev_seq = list(ld.launch_sequence)

                # Não propagamos item_conditions para os filhos.
                # A condição pertence ao GroupAction, e os filhos ficam dentro dele.
                self._process_item(ld, child, conditions)

                new_ids = [aid for aid in ld.launch_sequence if aid not in prev_seq]
                child_ids.extend(new_ids)

                for aid in new_ids:
                    ld.launch_sequence.remove(aid)

            group.children = child_ids
            
    def _make_node_action(self, item, conditions=None):
        pkg = item.get("package") or item.get("pkg")
        exe = item.get("exec") or item.get("executable")
        name = item.get("name")
        ns = item.get("namespace")
        params = {p["name"]: self._sub(p.get("value")) for p in item.get("params", []) if isinstance(p, dict)}
        remaps = [
            Remapping(from_topic=r.get("from", ""), to_topic=self._sub(r.get("to", "")))
            for r in item.get("remaps", []) if isinstance(r, dict)
        ]
        
        cond_list = list(conditions or [])

        return NodeAction(
            id=self._id_gen.generate(f"Node(pkg={pkg},exec={exe},name={name})"),
            action_type=ActionType.NODE,
            package=self._sub(pkg),
            executable=self._sub(exe),
            name=self._sub(name) if name else None,
            namespace=self._sub(ns) if ns else None,
            parameters=params,
            remappings=remaps,
            conditions=cond_list,
            provenance=self._provenance(),
        )

    def element(self, items): return items[0]
    def node_content(self, items): return items[0]
    def node(self, items): return items[0]

    def empty_node(self, items):
        attrs = dict(items)
        return {"type": "node", "pkg": attrs.get("pkg"), "exec": attrs.get("exec"),
                "name": attrs.get("name"), "namespace": attrs.get("namespace"),
                "if": attrs.get("if"), "unless": attrs.get("unless"), "params": [], "remaps": []}

    def full_node(self, items):
        attrs = {}; remaps = []; params = []
        for item in items:
            if isinstance(item, dict):
                if item.get("type") == "remap": remaps.append(item)
                elif item.get("type") == "param": params.append(item)
            elif isinstance(item, tuple):
                attrs[item[0]] = item[1]
        return {"type": "node", "pkg": attrs.get("pkg"), "exec": attrs.get("exec"),
                "name": attrs.get("name"), "namespace": attrs.get("namespace"),
                "if": attrs.get("if"), "unless": attrs.get("unless"),
                "params": params, "remaps": remaps}

    def remap(self, items):
        attrs = dict(items)
        return {"type": "remap", "from": attrs.get("from"), "to": attrs.get("to")}

    def param(self, items):
        attrs = dict(items)
        return {"type": "param", "name": attrs.get("name"), "value": attrs.get("value")}

    def let(self, items):
        attrs = dict(items)
        return {
            "type": "let",
            "name": attrs.get("name"),
            "value": attrs.get("value"),
            "if": attrs.get("if"),
            "unless": attrs.get("unless"),
        }

    def executable(self, items):
        attrs = {}; envs = []
        for item in items:
            if isinstance(item, dict) and item.get("type") == "env": envs.append(item)
            elif isinstance(item, tuple): attrs[item[0]] = item[1]
        return {"type": "executable", "cmd": attrs.get("cmd"), "cwd": attrs.get("cwd"), "env": envs}

    def env(self, items):
        attrs = dict(items)
        return {"type": "env", "name": attrs.get("name"), "value": attrs.get("value")}

    def set_env(self, items):
        attrs = dict(items)
        return {
            "type": "set_env",
            "name": attrs.get("name"),
            "value": attrs.get("value"),
            "if": attrs.get("if"),
            "unless": attrs.get("unless"),
        }

    def set_parameter(self, items):
        attrs = dict([i for i in items if isinstance(i, tuple)])
        return {
            "type": "set_parameter",
            "name": attrs.get("name"),
            "value": attrs.get("value"),
            "target_scope": attrs.get("target_scope", "local"),
            "if": attrs.get("if"),
            "unless": attrs.get("unless"),
        }

    def unset_env(self, items):
        attrs = dict(items)
        return {"type": "unset_env", "name": attrs.get("name")}

    def include(self, items):
        attrs = {}; args = []
        for item in items:
            if isinstance(item, dict) and item.get("type") == "arg": args.append(item)
            elif isinstance(item, tuple): attrs[item[0]] = item[1]
        return {
            "type": "include",
            "file": attrs.get("file"),
            "args": args,
            "if": attrs.get("if"),
            "unless": attrs.get("unless"),
        }
    
    def arg(self, items):
        attrs = dict(items)
        return {"type": "arg", "name": attrs.get("name"), "default": attrs.get("default"),
                "description": attrs.get("description")}

    def push_ros_namespace(self, items):
        attrs = dict(items)
        return {
            "type": "push_namespace",
            "namespace": attrs.get("namespace"),
            "if": attrs.get("if"),
            "unless": attrs.get("unless"),
        }
    
    def group(self, items):
        attrs = {}
        children = []

        for item in items:
            if isinstance(item, tuple):
                attrs[item[0]] = item[1]
            elif isinstance(item, list):
                children.extend(item)
            elif item is not None:
                children.append(item)

        return {
            "type": "group",
            "children": children,
            "namespace": attrs.get("namespace"),
            "if": attrs.get("if"),
            "unless": attrs.get("unless"),
        }

    def attribute(self, items):
        key = str(items[0])
        value = items[1][1:-1]
        return (key, value)