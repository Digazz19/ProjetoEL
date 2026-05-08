"""
transformerPython.py — Layer 2

Transformer Lark para launch files Python.
Produz um LaunchDescription Layer 2 conforme a especificação HAROS.
"""

from lark import Transformer


import re as _re


def _parse_condition_to_ir(condition_str: str) -> list:
    """Converte string de condição Python para IR Layer 2."""
    s = condition_str.strip()
    # or
    parts = _re.split(r'\s+or\s+', s)
    if len(parts) > 1:
        result = _parse_condition_to_ir(parts[0])
        for p in parts[1:]:
            result = ["or", result, _parse_condition_to_ir(p)]
        return result
    # and
    parts = _re.split(r'\s+and\s+', s)
    if len(parts) > 1:
        result = _parse_condition_to_ir(parts[0])
        for p in parts[1:]:
            result = ["and", result, _parse_condition_to_ir(p)]
        return result
    # not
    m = _re.match(r'^not\s+(.+)$', s)
    if m:
        return ["not", _parse_condition_to_ir(m.group(1))]
    # comparações
    for op, ir_op in [("==", "eq"), ("!=", "neq"), ("<=", "lte"), (">=", "gte"), ("<", "lt"), (">", "gt")]:
        if op in s:
            left, right = s.split(op, 1)
            left = left.strip()
            right = right.strip().strip("\'\"")
            return [ir_op, _parse_var_ir(left), right]
    return ["truthy", _parse_var_ir(s)]


def _parse_var_ir(name: str) -> list:
    name = name.strip()
    if name.isupper():
        return ["env_get", name]
    if name.startswith("os.environ"):
        m = _re.search(r"['\"]([\w]+)[\'\"]", name)
        return ["env_get", m.group(1) if m else name]
    if "LaunchConfiguration" in name:
        m = _re.search(r"['\"]([\w]+)[\'\"]", name)
        return ["launch_arg_get", m.group(1) if m else name]
    return ["var_get", name]


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


class LaunchPythonTransformer(Transformer):

    def __init__(self, file_path: str = "unknown.launch.py"):
        super().__init__()
        self._file_path = file_path
        self._file_id = ActionIDGenerator.file_id_from_path(file_path)
        self._id_gen = ActionIDGenerator(self._file_id)
        # Estado intermédio (igual ao transformer antigo)
        self.variables = {}
        self.launch_descriptions = {}
        # LaunchDescription Layer 2 em construção
        self._ld = None

    def _provenance(self, confidence: float = 1.0) -> ElementProvenance:
        return ElementProvenance(
            extraction_method="static_analysis",
            source_location=SourceLocation(file=self._file_path),
            confidence=confidence,
        )

    def _condition_expr_to_ir(self, expr):
        expr = self._resolve(expr)

        if isinstance(expr, dict):
            if expr.get("type") == "launch_config":
                return ["eq", ["launch_arg_get", expr.get("name", "")], "true"]

            if expr.get("type") == "env_var":
                return ["truthy", ["env_get", expr.get("name", "")]]

            if expr.get("type") == "var":
                return ["truthy", ["var_get", expr.get("name", "")]]

        if isinstance(expr, bool):
            return ["literal", expr]

        return _parse_condition_to_ir(str(expr))

    def _sub(self, value) -> LaunchSubstitution:
        """Converte um valor raw para LaunchSubstitution."""
        if isinstance(value, LaunchSubstitution):
            return value
        if value is None:
            return LaunchSubstitution.literal(None)
        if isinstance(value, bool):
            return LaunchSubstitution.literal(value)
        if isinstance(value, (int, float)):
            return LaunchSubstitution.literal(value)
        if isinstance(value, dict):
            t = value.get("type")
            if t == "var":
                # Tentar resolver a variável
                name = value.get("name", "")
                if name in self.variables:
                    return self._sub(self.variables[name])
                return LaunchSubstitution.argument_reference(name)
            if t == "launch_config":
                return LaunchSubstitution.argument_reference(
                    value.get("name", ""), value.get("default")
                )
            if t == "env_var":
                return LaunchSubstitution.environment_variable(
                    value.get("name", ""), value.get("default")
                )
            if t == "file_path":
                return LaunchSubstitution.file_path(
                    value.get("package", ""),
                    value.get("relative_path", "")
                )

            if t == "path_join":
                return LaunchSubstitution.expression([
                    "path_join",
                    *value.get("parts", [])
                ])
        return LaunchSubstitution.literal(str(value)) if value is not None else LaunchSubstitution.literal(None)

    def _make_node_action(self, node_data: dict, condition: str = None) -> NodeAction:
        """Cria um NodeAction a partir de um dict de node."""
        pkg = node_data.get("package") or node_data.get("pkg")
        exe = node_data.get("executable") or node_data.get("exec")
        name = node_data.get("name")
        ns = node_data.get("namespace")

        # Parâmetros
        params = {}
        raw_params = node_data.get("params") or node_data.get("parameters") or []
        if isinstance(raw_params, list):
            for p in raw_params:
                p = self._resolve(p)
                if isinstance(p, dict):
                    for k, v in p.items():
                        if k != "type":
                            params[str(k)] = self._sub(v)
                elif hasattr(p, 'name') and hasattr(p, 'value'):
                    params[str(p.name)] = self._sub(str(p.value))
        elif isinstance(raw_params, dict):
            for k, v in raw_params.items():
                params[str(k)] = self._sub(v)

        # Remaps
        remaps = []
        for r in (node_data.get("remappings") or []):
            r = self._resolve(r)
            if isinstance(r, tuple) and len(r) == 2:
                remaps.append(Remapping(from_topic=str(r[0]), to_topic=self._sub(str(r[1]))))
            elif isinstance(r, dict) and "src" in r:
                remaps.append(Remapping(from_topic=str(r["src"]), to_topic=self._sub(str(r["dst"]))))

        # Condições
        cond_list = []

        raw_condition = condition or node_data.get("condition")

        if raw_condition:
            resolved_condition = self._resolve(raw_condition)

            if isinstance(resolved_condition, dict) and resolved_condition.get("type") == "if_condition":
                cond_list = [resolved_condition.get("condition")]
            elif isinstance(resolved_condition, dict) and resolved_condition.get("type") == "unless_condition":
                cond_list = [["not", resolved_condition.get("condition")]]
            else:
                try:
                    cond_list = [_parse_condition_to_ir(str(resolved_condition))]
                except Exception:
                    cond_list = [["symbolic", str(resolved_condition)]]

        # ros_arguments — converter para LaunchSubstitution e serializar
        ros_args = []
        raw_args = node_data.get("arguments")
        if isinstance(raw_args, list):
            for a in raw_args:
                if a is None:
                    continue
                resolved = self._resolve(a)
                sub = self._sub(resolved)
                ros_args.append(sub.display())
        elif raw_args is not None:
            ros_args = [self._sub(self._resolve(raw_args)).display()]

        # launch_prefix
        launch_prefix = node_data.get("launch_prefix")
        if launch_prefix:
            launch_prefix = str(self._resolve(launch_prefix))

        snippet = f"Node(pkg={pkg},exec={exe},name={name})"
        return NodeAction(
            id=self._id_gen.generate(snippet),
            action_type=ActionType.NODE,
            package=self._sub(pkg),
            executable=self._sub(exe),
            name=self._sub(name) if name else None,
            namespace=self._sub(ns) if ns else None,
            parameters=params,
            remappings=remaps,
            ros_arguments=ros_args,
            launch_prefix=launch_prefix,
            conditions=cond_list,
            provenance=self._provenance(0.9 if condition else 1.0),
        )

    # -----------------------------------------------------------------------
    # Regras de gramática (igual ao transformer antigo)
    # -----------------------------------------------------------------------

    def start(self, items):
        ld_id = f"launch_desc_{self._file_id}"
        self._ld = LaunchDescription(
            id=ld_id,
            launch_file_id=self._file_id,
            format="python",
            provenance=ElementProvenance(
                extraction_method="static_analysis",
                source_location=SourceLocation(file=self._file_path),
                confidence=0.85,
            ),
        )
        for item in items:
            self._process_top_level(item)
        return self._ld

    def stmt(self, items):
        return items[0] if items else None

    def import_stmt(self, items): return None
    def import_list(self, items): return items
    def import_item(self, items): return None
    def dotted_name(self, items): return ".".join(str(x) for x in items)
    def funcdef(self, items): return {"type": "function", "body": items[-1]}
    def suite(self, items): return [item for item in items if item is not None]
    def func_stmt(self, items): return items[0] if items else None
    def assign_stmt(self, items): return ("assign", str(items[0]), items[1])
    def expr_stmt(self, items): return items[0]
    def return_stmt(self, items): return ("return", items[0])
    def method_call(self, items):
        # items[0] = objecto, items[1] = método, items[2] = argumento (opcional)
        # Mas a gramática define: NAME "." "add_action" "(" expr ")"
        # Para append precisamos de uma regra mais genérica
        return {"type": "add_action", "target": str(items[0]), "action": items[1]}

    def list_append(self, items):
        # NAME.append(expr) — adicionar item a uma lista variável
        return {"type": "list_append", "target": str(items[0]), "item": items[1]}

    def list_append_stmt(self, items):
        # list_append_stmt: NAME "." "append" "(" expr ")" _NEWLINE
        return {"type": "list_append", "target": str(items[0]), "item": items[1]}
    def qualified_name(self, items): return ".".join(str(x) for x in items)
    def call(self, items): return self._build_call(items)
    def arguments(self, items): return items
    def kw_argument(self, items): return (str(items[0]), items[1])
    def pos_argument(self, items): return items[0]
    def list(self, items):
        return [i for i in items if i is not None]
    def tuple(self, items): return tuple(items)

    def dict(self, items):
        result = {}
        for item in items:
            if isinstance(item, tuple) and len(item) == 2:
                result[item[0]] = item[1]
        return result

    def dict_call(self, items): return f"{items[0]}.{items[1]}()"
    def dict_item(self, items): return (items[0], items[1])

    def list_add(self, items):
        result = []
        for item in items:
            if isinstance(item, list):
                result.extend(item)
            elif isinstance(item, dict) and item.get("type") == "var":
                # Variável não resolvida — incluir para resolver mais tarde
                result.append(item)
        return result

    def concat_string(self, items):
        parts = []
        for item in items:
            s = str(item)
            if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
                s = s[1:-1]
            parts.append(s)
        return ''.join(parts)

    def top_assign(self, items): return None
    def class_def(self, items): return None
    def extra_funcdef(self, items): return None
    def with_stmt(self, items): return None
    def closing_paren(self, items): return None
    def ignored_stmt(self, items): return None
    def string_call(self, items): return None
    def subscript(self, items): return f"{items[0]}[...]"
    def qualified_var(self, items): return ".".join(str(i) for i in items)

    def if_stmt(self, items):
        results = []
        hdr = str(items[0])
        condition = hdr[3:].rstrip(':').strip()
        suite = items[1] if len(items) > 1 else []
        for item in (suite if isinstance(suite, list) else [suite]):
            if item is not None:
                results.append(("if", condition, item))
        for clause in items[2:]:
            if isinstance(clause, list):
                results.extend(clause)
        return ("if_block", results)

    def elif_clause(self, items):
        hdr = str(items[0])
        condition = hdr[5:].rstrip(':').strip()
        suite = items[1] if len(items) > 1 else []
        results = []
        for item in (suite if isinstance(suite, list) else [suite]):
            if item is not None:
                results.append(("if", condition, item))
        return results

    def else_clause(self, items):
        suite = items[0] if items else []
        results = []
        for item in (suite if isinstance(suite, list) else [suite]):
            if item is not None:
                results.append(("else", None, item))
        return results

    def launch_description(self, items):
        if not items:
            return {"type": "launch_description", "actions": []}
        source = self._resolve(items[0])
        actions = []
        if isinstance(source, list):
            for item in source:
                resolved = self._resolve(item)
                if self._is_action(resolved):
                    actions.append(resolved)
                elif isinstance(resolved, dict) and resolved.get("type") == "var":
                    actions.append(resolved)
        elif isinstance(source, dict) and source.get("type") == "var":
            # Variável não resolvida (ex: declared_args) — guardar como referência pendente
            actions.append(source)
        elif source is not None and self._is_action(source):
            actions = [source]
        return {"type": "launch_description", "actions": actions}

    def string(self, items):
        value = str(items[0])
        return value[1:-1]

    def number(self, items):
        text = str(items[0])
        return float(text) if "." in text else int(text)

    def true(self, _): return True
    def false(self, _): return False
    def none(self, _): return None

    def var(self, items):
        return {"type": "var", "name": str(items[0])}

    # -----------------------------------------------------------------------
    # Lógica de resolução (igual ao transformer antigo)
    # -----------------------------------------------------------------------

    def _build_call(self, items):
        qname = items[0]
        args = []
        kwargs = {}
        if len(items) > 1 and items[1] is not None:
            for item in items[1]:
                if item is None:
                    continue
                if isinstance(item, tuple) and len(item) == 2 and isinstance(item[0], str):
                    kwargs[item[0]] = item[1]
                else:
                    args.append(item)
        return self._specialize_call(qname, args, kwargs)

    def _extract_launch_arguments(self, raw):
        raw = self._resolve(raw)

        if raw is None:
            return []

        # Caso: {'robot_name': 'robot1'}
        if isinstance(raw, dict):
            return [
                {
                    "name": str(k),
                    "value": self._resolve(v),
                }
                for k, v in raw.items()
                if k != "type"
            ]

        # Caso: [('robot_name', 'robot1')]
        if isinstance(raw, list):
            result = []
            for item in raw:
                item = self._resolve(item)

                if isinstance(item, tuple) and len(item) == 2:
                    result.append({
                        "name": str(item[0]),
                        "value": self._resolve(item[1]),
                    })

                elif isinstance(item, dict) and item.get("name"):
                    result.append({
                        "name": str(item.get("name")),
                        "value": self._resolve(item.get("value") or item.get("default")),
                    })

            return result

        # Caso frequente: {'robot_name': 'robot1'}.items()
        # Se a gramática estiver a transformar isto em string, não conseguimos
        # recuperar os pares sem melhorar a gramática.
        return []
    
    def _specialize_call(self, qname, args, kwargs):
        short = qname.split(".")[-1]

        if short == "Node":
            return {
                "type": "node_raw",
                "package": kwargs.get("package", kwargs.get("pkg")),
                "executable": kwargs.get("executable", kwargs.get("exec")),
                "name": kwargs.get("name"),
                "namespace": kwargs.get("namespace"),
                "params": kwargs.get("parameters", kwargs.get("params", [])),
                "remappings": kwargs.get("remappings", []),
                "arguments": kwargs.get("arguments", kwargs.get("ros_arguments")),
                "launch_prefix": kwargs.get("launch_prefix"),
                "condition": kwargs.get("condition"),
            }

        if short == "DeclareLaunchArgument":
            name = self._resolve(args[0]) if args else self._resolve(kwargs.get("name"))
            default = kwargs.get("default_value", kwargs.get("default"))
            desc = kwargs.get("description")
            choices = kwargs.get("choices")
            choices_resolved = self._resolve(choices) if choices is not None else None
            if isinstance(choices_resolved, (list, tuple)):
                choices_resolved = [str(c) for c in choices_resolved]
            return {"type": "arg", "name": name, "default": self._resolve(default),
                    "description": self._resolve(desc), "choices": choices_resolved}

        if short == "IncludeLaunchDescription":
            source_value = args[0] if args else kwargs.get("launch_description_source")

            raw_launch_args = kwargs.get("launch_arguments", [])
            launch_args = self._extract_launch_arguments(raw_launch_args)

            return {
                "type": "include",
                "file": source_value,
                "args": launch_args,
            }
            
        if short == "LaunchDescription":
            # launch.LaunchDescription([...]) chamado como call genérico
            actions_raw = args[0] if args else []
            actions = self._resolve(actions_raw) if actions_raw else []
            if isinstance(actions, dict) and actions.get("type") == "var":
                actions = [actions]
            elif not isinstance(actions, list):
                actions = []
            return {"type": "launch_description", "actions": actions}

        if short == "PushRosNamespace":
            ns = self._resolve(args[0]) if args else self._resolve(kwargs.get("namespace"))
            return {"type": "push_namespace", "namespace": ns}

        if short == "GroupAction":
            children = self._resolve(args[0]) if args else self._resolve(kwargs.get("actions", []))
            if not isinstance(children, list):
                children = [children] if children else []
            return {"type": "group_action", "children": children}

        if short == "ComposableNode":
            # ComposableNode usa plugin em vez de executable
            pkg = kwargs.get("package")
            plugin = kwargs.get("plugin")  # ex: "camera::CameraNode"
            name = kwargs.get("name")
            ns = kwargs.get("namespace")
            params = kwargs.get("parameters", [])
            remaps = kwargs.get("remappings", [])
            return {
                "type": "node_raw",
                "package": pkg,
                "executable": plugin,  # usar plugin como executable
                "name": name,
                "namespace": ns,
                "params": params,
                "remappings": remaps,
                "arguments": None,
                "launch_prefix": None,
                "is_composable": True,
            }

        if short == "LoadComposableNodes":
            # LoadComposableNodes carrega nodes num container existente
            # Para análise estática, os composable nodes são extraídos da mesma forma
            nodes_raw = kwargs.get("composable_node_descriptions", [])
            if isinstance(nodes_raw, list):
                # Lista inline — resolver directamente
                nodes = [self._resolve(n) for n in nodes_raw]
            else:
                nodes_raw_resolved = self._resolve(nodes_raw)
                nodes = nodes_raw_resolved if isinstance(nodes_raw_resolved, list) else []
            target = kwargs.get("target_container")
            return {
                "type": "load_composable_nodes",
                "target_container": target,
                "composable_nodes": nodes,
            }

        if short == "ComposableNodeContainer":
            pkg = kwargs.get("package")
            exe = kwargs.get("executable")
            name = kwargs.get("name")
            ns = kwargs.get("namespace")
            # Guardar a referência para resolver depois (quando as variables estão populadas)
            nodes_raw = kwargs.get("composable_node_descriptions", [])
            return {
                "type": "composable_container",
                "package": pkg,
                "executable": exe,
                "name": name,
                "namespace": ns,
                "composable_nodes_ref": nodes_raw,  # resolver em _consume_actions
            }

        if short == "SetParameter":
            name = self._resolve(args[0]) if args else self._resolve(kwargs.get("name"))
            value = self._resolve(args[1]) if len(args) > 1 else self._resolve(kwargs.get("value"))

            return {
                "type": "set_parameter",
                "name": name,
                "value": value,
                "target_scope": "local",
            }
        
        if short == "SetEnvironmentVariable":
            name = self._resolve(args[0]) if args else self._resolve(kwargs.get("name"))
            value = self._resolve(args[1]) if len(args) > 1 else self._resolve(kwargs.get("value"))
            return {"type": "set_env", "name": name, "value": value}

        if short == "UnsetEnvironmentVariable":
            name = self._resolve(args[0]) if args else self._resolve(kwargs.get("name"))
            return {"type": "unset_env", "name": name}

        if short == "ExecuteProcess":
            return {
                "type": "executable",
                "cmd": self._resolve(kwargs.get("cmd", args[0] if args else None)),
                "cwd": self._resolve(kwargs.get("cwd")),
                "env": [],
            }

        if short in {"PythonLaunchDescriptionSource", "XMLLaunchDescriptionSource", "YAMLLaunchDescriptionSource"}:
            path_value = args[0] if args else kwargs.get("location")
            return {"type": "launch_source", "source_type": short, "path": path_value}

        if short == "IfCondition":
            expr = self._resolve(args[0]) if args else self._resolve(kwargs.get("predicate"))
            return {
                "type": "if_condition",
                "condition": self._condition_expr_to_ir(expr),
            }

        if short == "UnlessCondition":
            expr = self._resolve(args[0]) if args else self._resolve(kwargs.get("predicate"))
            return {
                "type": "unless_condition",
                "condition": self._condition_expr_to_ir(expr),
            }
        
        return self._symbolic(qname, args, kwargs)

    def _symbolic(self, qname, args, kwargs):
        short = qname.split(".")[-1]

        if short == "LaunchConfiguration":
            name = self._resolve(args[0]) if args else self._resolve(
                kwargs.get("name", kwargs.get("variable_name"))
            )
            default = kwargs.get("default_value", kwargs.get("default"))

            return {
                "type": "launch_config",
                "name": name,
                "default": self._resolve(default),
            }

        if short == "EnvironmentVariable":
            name = self._resolve(args[0]) if args else self._resolve(
                kwargs.get("name", kwargs.get("variable_name"))
            )
            default = kwargs.get("default_value", kwargs.get("default"))

            return {
                "type": "env_var",
                "name": name,
                "default": self._resolve(default),
            }

        if short == "FindPackageShare":
            package = self._resolve(args[0]) if args else self._resolve(
                kwargs.get("package")
            )

            return {
                "type": "find_pkg_share",
                "package": package,
            }

        if short == "PathJoinSubstitution":
            parts = self._resolve(args[0]) if args else self._resolve(
                kwargs.get("substitutions", [])
            )

            if not isinstance(parts, list):
                parts = [parts]

            if parts and isinstance(parts[0], dict) and parts[0].get("type") == "find_pkg_share":
                package = parts[0].get("package")
                relative_parts = [str(self._resolve(p)) for p in parts[1:]]

                return {
                    "type": "file_path",
                    "package": package,
                    "relative_path": "/".join(relative_parts),
                }

            return {
                "type": "path_join",
                "parts": parts,
            }

        parts = [repr(self._resolve(a)) for a in args]
        parts.extend(f"{k}={repr(self._resolve(v))}" for k, v in kwargs.items())

        return f"{qname}({', '.join(parts)})"

    def _resolve(self, value):
        if isinstance(value, dict) and value.get("type") == "var":
            if value["name"] in self.variables:
                return self.variables[value["name"]]
            return value
        if isinstance(value, list):
            return [self._resolve(v) for v in value]
        if isinstance(value, tuple):
            return tuple(self._resolve(v) for v in value)
        if isinstance(value, dict):
            if value.get("type") in {"arg", "include", "set_env", "unset_env",
                                        "set_parameter",
                                      "executable", "add_action", "launch_source",
                                      "launch_config", "node_raw"}:
                return {k: self._resolve(v) for k, v in value.items()}
            return {self._resolve(k): self._resolve(v) for k, v in value.items()}
        return value

    def _is_action(self, value):
        if isinstance(value, dict):
            return value.get("type") in {"arg", "include", "set_env", "unset_env",
                                        "set_parameter",
                                        "executable", "node_raw", "push_namespace",
                                        "group_action", "composable_container",
                                        "load_composable_nodes"}
        return False

    def _process_top_level(self, item):
        if isinstance(item, dict) and item.get("type") == "function":
            self._process_function_body(item["body"])

    def _process_function_body(self, body):
        for stmt in body:
            if stmt is None:
                continue
            kind = stmt[0] if isinstance(stmt, tuple) else None
            if kind == "assign":
                _, name, value = stmt
                resolved = self._resolve(value)
                if isinstance(resolved, dict) and resolved.get("type") == "launch_description":
                    self.launch_descriptions[name] = resolved["actions"]
                else:
                    self.variables[name] = resolved
            elif kind == "if_block":
                _, branches = stmt
                for branch_kind, condition, item in branches:
                    self._process_if_item(item, condition)
            elif kind == "return":
                self._consume_return(stmt[1])
            elif isinstance(stmt, dict) and stmt.get("type") == "add_action":
                target = stmt["target"]
                action = self._resolve(stmt["action"])
                self.launch_descriptions.setdefault(target, []).append(action)
            elif isinstance(stmt, dict) and stmt.get("type") == "list_append":
                target = stmt["target"]
                item = self._resolve(stmt["item"])
                # Se a variável existe como lista, adicionar
                if target in self.variables and isinstance(self.variables[target], list):
                    self.variables[target].append(item)
                else:
                    # Criar nova lista com o item
                    self.variables.setdefault(target, [])
                    if isinstance(self.variables[target], list):
                        self.variables[target].append(item)

    def _process_if_item(self, item, condition):
        if item is None:
            return
        kind = item[0] if isinstance(item, tuple) else None
        if kind == "assign":
            _, name, value = item
            resolved = self._resolve(value)
            if isinstance(resolved, dict) and resolved.get("type") == "node_raw":
                action = self._make_node_action(resolved, condition)
                self._ld.add_action(action)
            elif isinstance(resolved, dict) and resolved.get("type") == "launch_description":
                for a in resolved.get("actions", []):
                    if isinstance(a, dict) and a.get("type") == "node_raw":
                        self._ld.add_action(self._make_node_action(a, condition))
            else:
                self.variables[name] = resolved
        elif kind == "return":
            self._consume_return(item[1])
        elif kind == "if_block":
            _, branches = item
            for branch_kind, nested_cond, nested_item in branches:
                combined = f"({condition}) and ({nested_cond})" if nested_cond else condition
                self._process_if_item(nested_item, combined)

    def _consume_return(self, value):
        resolved = self._resolve(value)
        if isinstance(resolved, dict) and resolved.get("type") == "launch_description":
            actions = resolved["actions"]
            # Flatten: resolver listas aninhadas (var refs resolvidas para listas)
            expanded = []
            for a in actions:
                if isinstance(a, list):
                    expanded.extend(a)
                elif isinstance(a, dict) and a.get("type") == "var":
                    var_val = self.variables.get(a["name"], [])
                    if isinstance(var_val, list):
                        expanded.extend(var_val)
                    elif var_val is not None:
                        expanded.append(var_val)
                else:
                    expanded.append(a)
            self._consume_actions(expanded)
        elif isinstance(resolved, str) and resolved in self.launch_descriptions:
            self._consume_actions(self.launch_descriptions[resolved])
        elif isinstance(value, dict) and value.get("type") == "var":
            name = value["name"]
            if name in self.launch_descriptions:
                self._consume_actions(self.launch_descriptions[name])
            elif name in self.variables:
                var_val = self.variables[name]
                if isinstance(var_val, list):
                    self._consume_actions(var_val)

    def _consume_actions(self, actions):
        for action in actions:
            # Resolver variáveis pendentes
            if isinstance(action, dict) and action.get("type") == "var":
                action = self._resolve(action)

            if isinstance(action, dict):
                t = action.get("type")

                if t == "node_raw":
                    self._ld.add_action(self._make_node_action(action))

                elif t == "arg":
                    name = action.get("name", "")
                    default = action.get("default")
                    desc = action.get("description")
                    choices = action.get("choices")
                    self._ld.add_action(DeclareArgumentAction(
                        id=self._id_gen.generate(f"arg_{name}"),
                        action_type=ActionType.DECLARE_ARGUMENT,
                        name=str(name) if name else "",
                        default_value=self._sub(default) if default is not None else None,
                        description=str(desc) if desc else None,
                        choices=choices if isinstance(choices, list) else None,
                        provenance=self._provenance(),
                    ))

                elif t == "include":
                    file_value = self._resolve(action.get("file"))
                    if isinstance(file_value, dict) and file_value.get("type") == "launch_source":
                        file_value = file_value.get("path")
                    file_value = self._resolve(file_value)
                    # Tentar extrair nome do ficheiro de forma legível
                    import re as _re2
                    file_str = "unknown"
                    if isinstance(file_value, list):
                        # ex: [ThisLaunchFileDir(), '/file.launch.py'] — pegar no último elemento literal
                        for part in reversed(file_value):
                            part = self._resolve(part)
                            if isinstance(part, str) and ('.launch' in part or part.endswith('.py')):
                                file_str = part.strip('/')
                                break
                        if file_str == "unknown":
                            file_str = str(file_value)
                    elif isinstance(file_value, str):
                        # Tentar extrair só o nome do ficheiro .launch.py/xml/yaml
                        import os as _os2
                        basename = _os2.path.basename(file_value)
                        if ".launch" in basename:
                            file_str = basename
                        else:
                            file_str = file_value
                    elif file_value is not None:
                        file_str = str(file_value)
                    included_id = ActionIDGenerator.file_id_from_path(file_str)
                    arg_mappings = {}
                    for arg in action.get("args", []):
                        if isinstance(arg, dict) and arg.get("name"):
                            arg_mappings[arg["name"]] = self._sub(arg.get("value") or arg.get("default"))
                    self._ld.add_action(IncludeAction(
                        id=self._id_gen.generate(f"include_{included_id}"),
                        action_type=ActionType.INCLUDE,
                        included_launch_id=f"launch_desc_{included_id}",
                        argument_mappings=arg_mappings,
                        provenance=self._provenance(),
                    ))

                elif t == "group_action":
                    children_items = action.get("children", [])
                    if not isinstance(children_items, list):
                        children_items = []
                    # Criar o GroupAction primeiro
                    group = GroupAction(
                        id=self._id_gen.generate("group_action"),
                        action_type=ActionType.GROUP,
                        provenance=self._provenance(0.9),
                    )
                    self._ld.add_action(group)
                    # Processar os filhos e capturar os seus IDs
                    prev_seq = list(self._ld.launch_sequence)
                    self._consume_actions(children_items)
                    new_ids = [aid for aid in self._ld.launch_sequence if aid not in prev_seq]
                    # Remover filhos da sequência principal e atribuir ao grupo
                    for aid in new_ids:
                        self._ld.launch_sequence.remove(aid)
                    group.children = new_ids

                elif t == "load_composable_nodes":
                    # Processar os composable nodes directamente
                    composable_nodes = action.get("composable_nodes", [])
                    if not isinstance(composable_nodes, list):
                        composable_nodes = [composable_nodes] if composable_nodes else []
                    if composable_nodes:
                        self._consume_actions(composable_nodes)

                elif t == "composable_container":
                    # O container em si é um node
                    pkg = action.get("package")
                    exe = action.get("executable")
                    name = action.get("name")
                    ns = action.get("namespace")
                    if pkg and exe:
                        container_node = {
                            "type": "node_raw",
                            "package": pkg,
                            "executable": exe,
                            "name": name,
                            "namespace": ns,
                            "params": [],
                            "remappings": [],
                            "arguments": None,
                            "launch_prefix": None,
                        }
                        self._ld.add_action(self._make_node_action(container_node))
                    # Resolver a referência aos composable nodes agora que as variables estão populadas
                    nodes_ref = action.get("composable_nodes_ref", [])
                    composable_nodes = self._resolve(nodes_ref)
                    if isinstance(composable_nodes, dict) and composable_nodes.get("type") == "var":
                        composable_nodes = self.variables.get(composable_nodes["name"], [])
                    if not isinstance(composable_nodes, list):
                        composable_nodes = [composable_nodes] if composable_nodes else []
                    if composable_nodes:
                        self._consume_actions(composable_nodes)

                elif t == "push_namespace":
                    ns = action.get("namespace")
                    self._ld.add_action(PushNamespaceAction(
                        id=self._id_gen.generate(f"push_ns_{ns}"),
                        action_type=ActionType.PUSH_NAMESPACE,
                        namespace=self._sub(ns),
                        provenance=self._provenance(),
                    ))

                elif t == "set_parameter":
                    name = action.get("name", "")
                    value = action.get("value")

                    self._ld.add_action(SetParameterAction(
                        id=self._id_gen.generate(f"set_param_{name}"),
                        action_type=ActionType.SET_PARAMETER,
                        name=str(name) if name else "",
                        value=self._sub(value),
                        target_scope=action.get("target_scope", "local"),
                        provenance=self._provenance(),
                    ))

                elif t == "set_env":
                    self._ld.add_action(SetParameterAction(
                        id=self._id_gen.generate(f"set_env_{action.get('name','')}"),
                        action_type=ActionType.SET_PARAMETER,
                        name=str(action.get("name", "")),
                        value=self._sub(action.get("value")),
                        target_scope="global",
                        provenance=self._provenance(),
                    ))

                elif t == "executable":
                    # ExecuteProcess modelado como NodeAction especial
                    cmd = action.get("cmd")
                    self._ld.add_action(NodeAction(
                        id=self._id_gen.generate(f"exec_{cmd}"),
                        action_type=ActionType.NODE,
                        package=LaunchSubstitution.literal("__executable__"),
                        executable=LaunchSubstitution.literal(str(cmd)),
                        provenance=self._provenance(),
                    ))