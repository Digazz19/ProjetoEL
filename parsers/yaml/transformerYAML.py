"""
transformerYAML.py — Layer 2

Transformer Lark para launch files YAML.
Produz um LaunchDescription Layer 2 conforme a especificação HAROS.
"""

from lark import Transformer
import re as _re

from models.layer2 import (
    LaunchDescription,
    LaunchSubstitution,
    ElementProvenance,
    SourceLocation,
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
class LaunchYAMLTransformer(Transformer):

    def __init__(self, file_path: str = "unknown.launch.yaml"):
        super().__init__()
        self._file_path = file_path
        self._file_id = ActionIDGenerator.file_id_from_path(file_path)
        self._id_gen = ActionIDGenerator(self._file_id)

    def _provenance(self, confidence: float = 1.0) -> ElementProvenance:
        return ElementProvenance(
            extraction_method="static_analysis",
            source_location=SourceLocation(file=self._file_path),
            confidence=confidence,
        )

    def _sub(self, value) -> LaunchSubstitution:
        import re
        if isinstance(value, LaunchSubstitution):
            return value
        if value is None:
            return LaunchSubstitution.literal(None)
        s = str(value)
        # $(var name) ou $(arg name)
        m = re.match(r'^\$\((var|arg)\s+(\S+)\)$', s)
        if m:
            return LaunchSubstitution.argument_reference(m.group(2))
        # $(env NAME)
        m = re.match(r'^\$\(env\s+(\S+)(?:\s+(.+))?\)$', s)
        if m:
            return LaunchSubstitution.environment_variable(m.group(1), m.group(2))
        # $(find-pkg-share pkg)/path
        m = re.match(r'^\$\(find-pkg-share\s+(\S+)\)/(.+)$', s)
        if m:
            return LaunchSubstitution.file_path(m.group(1), m.group(2))
        return LaunchSubstitution.literal(s)

    # -----------------------------------------------------------------------
    # Regras principais
    # -----------------------------------------------------------------------

    def start(self, items):
        for item in items:
            if isinstance(item, LaunchDescription):
                return item
        return items[-1] if items else None

    def launch(self, items):
        ld_id = f"launch_desc_{self._file_id}"
        ld = LaunchDescription(
            id=ld_id,
            launch_file_id=self._file_id,
            format="yaml",
            provenance=ElementProvenance(
                extraction_method="static_analysis",
                source_location=SourceLocation(file=self._file_path),
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

        if t == "node":
            ld.add_action(self._make_node_action(item, conditions))

        elif t == "arg":
            ld.add_action(DeclareArgumentAction(
                id=self._id_gen.generate(f"arg_{item.get('name','')}"),
                action_type=ActionType.DECLARE_ARGUMENT,
                name=item.get("name", ""),
                default_value=self._sub(item.get("default")) if item.get("default") is not None else None,
                description=item.get("description"),
                provenance=self._provenance(),
            ))

        elif t == "let":
            ld.add_action(SetParameterAction(
                id=self._id_gen.generate(f"let_{item.get('name','')}"),
                action_type=ActionType.SET_PARAMETER,
                name=item.get("name", ""),
                value=self._sub(item.get("value")),
                target_scope="local",
                provenance=self._provenance(),
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
                provenance=self._provenance(),
            )
            ld.add_action(action)

        elif t == "set_env":
            ld.add_action(SetParameterAction(
                id=self._id_gen.generate(f"set_env_{item.get('name','')}"),
                action_type=ActionType.SET_PARAMETER,
                name=item.get("name", ""),
                value=self._sub(item.get("value")),
                target_scope="global",
                provenance=self._provenance(),
            ))

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
                conditions=conditions or [],
                provenance=self._provenance(),
            ))

        elif t == "push_namespace":
            ns = item.get("namespace")
            action = PushNamespaceAction(
                id=self._id_gen.generate(f"push_ns_{ns}"),
                action_type=ActionType.PUSH_NAMESPACE,
                namespace=self._sub(ns) if ns else None,
                conditions=conditions or [],
                provenance=self._provenance(),
            )
            ld.add_action(action)

        elif t == "group":
            group_id = self._id_gen.generate("group")
            group = GroupAction(
                id=group_id,
                action_type=ActionType.GROUP,
                namespace=self._sub(item.get("namespace")) if item.get("namespace") else None,
                conditions=conditions or [],
                provenance=self._provenance(),
            )
            ld.add_action(group)
            child_ids = []
            for child in item.get("children", []):
                prev_seq = list(ld.launch_sequence)
                self._process_item(ld, child, conditions)
                new_ids = [aid for aid in ld.launch_sequence if aid not in prev_seq]
                child_ids.extend(new_ids)
                for aid in new_ids:
                    ld.launch_sequence.remove(aid)
            group.children = child_ids

    def _make_node_action(self, item, conditions=None):
        pkg = item.get("pkg")
        exe = item.get("exec")
        name = item.get("name")
        ns = item.get("namespace")

        # Parâmetros
        params = {}
        for p in item.get("params", []):
            if hasattr(p, 'name'):
                params[p.name] = self._sub(str(p.value))
            elif isinstance(p, dict):
                params[p["name"]] = self._sub(p.get("value"))

        # Remaps
        remaps = []
        for r in item.get("remaps", []):
            if isinstance(r, tuple) and len(r) == 2:
                remaps.append(Remapping(
                    from_topic=str(r[0]),
                    to_topic=self._sub(str(r[1])),
                ))
            elif isinstance(r, dict):
                remaps.append(Remapping(
                    from_topic=r.get("from", ""),
                    to_topic=self._sub(r.get("to", "")),
                ))

        cond_list = list(conditions or [])

        if item.get("if"):
            cond_list.append(_parse_launch_condition_to_ir(item["if"]))

        if item.get("unless"):
            cond_list.append(["not", _parse_launch_condition_to_ir(item["unless"])])
            
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

    # -----------------------------------------------------------------------
    # Regras de gramática (mesma estrutura do transformer antigo)
    # -----------------------------------------------------------------------

    def element(self, items):
        for item in items:
            if isinstance(item, (dict, list)):
                return item

    def node_content(self, items):
        for item in items:
            if isinstance(item, (dict, tuple)):
                return item

    def include_content(self, items):
        for item in items:
            if isinstance(item, (dict, tuple)):
                return item

    def exec_content(self, items):
        for item in items:
            if isinstance(item, (dict, tuple)):
                return item

    def node(self, items):
        attrs = {}
        remaps = []
        params = []
        for item in items:
            if isinstance(item, dict):
                if item.get("type") == "remap":
                    remaps.extend(item["data"])
                elif item.get("type") == "param":
                    params.extend(item["data"])
            elif isinstance(item, tuple):
                attrs[item[0]] = item[1]
        return {
            "type": "node",
            "pkg": attrs.get("pkg"),
            "exec": attrs.get("exec"),
            "name": attrs.get("name"),
            "namespace": attrs.get("namespace"),
            "if": attrs.get("if"),
            "unless": attrs.get("unless"),
            "params": params,
            "remaps": remaps,
        }

    def include(self, items):
        attrs = {}
        args = []
        for item in items:
            if isinstance(item, dict) and item.get("type") == "args":
                args.extend(item["data"])
            elif isinstance(item, tuple):
                attrs[item[0]] = item[1]
        return {"type": "include", "file": attrs.get("file"), "args": args}

    def push_ros_namespace(self, items):
        attrs = dict([i for i in items if isinstance(i, tuple)])
        return {
            "type": "push_namespace",
            "namespace": attrs.get("namespace"),
        }
    
    def set_parameter(self, items):
        attrs = dict([i for i in items if isinstance(i, tuple)])
        return {
            "type": "set_parameter",
            "name": attrs.get("name"),
            "value": attrs.get("value"),
            "target_scope": attrs.get("target_scope", "local"),
        }
    
    def group(self, items):
        children = [i for i in items if isinstance(i, (dict, list))]
        return {"type": "group", "children": children}

    def arg(self, items):
        attrs = dict([i for i in items if isinstance(i, tuple)])
        return {
            "type": "arg",
            "name": attrs.get("name"),
            "default": attrs.get("default", attrs.get("value")),
        }

    def let(self, items):
        attrs = dict([i for i in items if isinstance(i, tuple)])
        return {"type": "let", "name": attrs.get("name"), "value": attrs.get("value")}

    def set_env(self, items):
        attrs = dict([i for i in items if isinstance(i, tuple)])
        return {"type": "set_env", "name": attrs.get("name"), "value": attrs.get("value")}

    def unset_env(self, items):
        attrs = dict([i for i in items if isinstance(i, tuple)])
        return {"type": "unset_env", "name": attrs.get("name")}

    def executable(self, items):
        attrs = {}
        envs = []
        for item in items:
            if isinstance(item, dict) and item.get("type") == "env":
                envs.extend(item["data"])
            elif isinstance(item, tuple):
                attrs[item[0]] = item[1]
        return {"type": "executable", "cmd": attrs.get("cmd"), "cwd": attrs.get("cwd"), "env": envs}

    def param(self, items):
        valid = [i for i in items if isinstance(i, list)]
        from models.layer2 import LaunchSubstitution
        params = [
            {"name": dict(i).get("name"), "value": dict(i).get("value")}
            for i in valid
        ]
        return {"type": "param", "data": params}

    def remap(self, items):
        valid = [i for i in items if isinstance(i, list)]
        remaps = [(dict(i).get("from"), dict(i).get("to")) for i in valid]
        return {"type": "remap", "data": remaps}

    def env(self, items):
        valid = [i for i in items if isinstance(i, list)]
        envs = [{"name": dict(i).get("name"), "value": dict(i).get("value")} for i in valid]
        return {"type": "env", "data": envs}

    def args(self, items):
        valid = [i for i in items if isinstance(i, list)]
        args = [{"type": "arg", "name": dict(i).get("name"), "value": dict(i).get("value")} for i in valid]
        return {"type": "args", "data": args}

    def dict_item(self, items):
        return [item for item in items if isinstance(item, tuple)]

    def attribute(self, items):
        key = str(items[0])
        value = str(items[1])
        if (value.startswith('"') and value.endswith('"')) or \
           (value.startswith("'") and value.endswith("'")):
            value = value[1:-1]
        return (key, value)