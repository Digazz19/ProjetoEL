from lark import Transformer
from models.architectureROS import ArchitectureROS, Node, Param, Remapping


class LaunchPythonTransformer(Transformer):
    def __init__(self):
        super().__init__()
        self.arch = ArchitectureROS()
        self.variables = {}
        self.launch_descriptions = {}

    def start(self, items):
        for item in items:
            self._process_top_level(item)
        self.arch.resolve()
        return self.arch

    def stmt(self, items):
        return items[0] if items else None

    def import_stmt(self, items):
        return None

    def import_list(self, items):
        return items

    def import_item(self, items):
        return None

    def dotted_name(self, items):
        return ".".join(str(x) for x in items)

    def funcdef(self, items):
        return {"type": "function", "body": items[-1]}

    def extra_funcdef(self, items):
        return None

    def top_assign(self, items):
        return None

    def class_def(self, items):
        return None

    def with_stmt(self, items):
        return None

    def suite(self, items):
        return [item for item in items if item is not None]

    def func_stmt(self, items):
        return items[0] if items else None

    def assign_stmt(self, items):
        return ("assign", str(items[0]), items[1])

    def expr_stmt(self, items):
        return items[0]

    def return_stmt(self, items):
        return ("return", items[0])

    def method_call(self, items):
        return {"type": "add_action", "target": str(items[0]), "action": items[1]}

    def launch_description(self, items):
        if not items:
            return {"type": "launch_description", "actions": []}
        source = self._resolve(items[0])
        actions = []
        if isinstance(source, list):
            actions = [a for a in source if self._is_action(a)]
        elif source is not None and self._is_action(source):
            actions = [source]
        return {"type": "launch_description", "actions": actions}

    def qualified_name(self, items):
        return ".".join(str(x) for x in items)

    def call(self, items):
        return self._build_call(items)

    def dict_call(self, items):
        return f"{items[0]}.{items[1]}()"

    def list_add(self, items):
        result = []
        for item in items:
            if isinstance(item, list):
                result.extend(item)
        return result

    def concat_string(self, items):
        parts = []
        for item in items:
            s = str(item)
            if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
                s = s[1:-1]
            parts.append(s)
        return ''.join(parts)

    def arguments(self, items):
        return items

    def kw_argument(self, items):
        return (str(items[0]), items[1])

    def pos_argument(self, items):
        return items[0]

    def list(self, items):
        return list(items)

    def tuple(self, items):
        return tuple(items)

    def dict(self, items):
        result = {}
        for item in items:
            if isinstance(item, tuple) and len(item) == 2:
                result[item[0]] = item[1]
        return result

    def dict_item(self, items):
        return (items[0], items[1])

    def string(self, items):
        value = str(items[0])
        if (value.startswith('"') and value.endswith('"')) or \
           (value.startswith("'") and value.endswith("'")):
            return value[1:-1]
        return value

    def number(self, items):
        text = str(items[0])
        if "." in text:
            return float(text)
        return int(text)

    def true(self, _):
        return True

    def false(self, _):
        return False

    def none(self, _):
        return None

    def var(self, items):
        return {"type": "var", "name": str(items[0])}

    def _build_call(self, items):
        qname = items[0]
        args = []
        kwargs = {}
        if len(items) > 1:
            for item in items[1]:
                if isinstance(item, tuple) and len(item) == 2 and isinstance(item[0], str):
                    kwargs[item[0]] = item[1]
                else:
                    args.append(item)
        return self._specialize_call(qname, args, kwargs)

    def _specialize_call(self, qname, args, kwargs):
        short = qname.split(".")[-1]
        if short == "Node":
            return Node(
                name=kwargs.get("name"),
                package=kwargs.get("package", kwargs.get("pkg")),
                exec=kwargs.get("executable", kwargs.get("exec")),
                namespace=kwargs.get("namespace"),
                remappings=self._convert_remaps(kwargs.get("remappings", [])),
                params=kwargs.get("parameters", kwargs.get("params", [])),
                args=kwargs.get("arguments", kwargs.get("ros_arguments"))
            )
        if short == "DeclareLaunchArgument":
            name = self._resolve(args[0]) if args else self._resolve(kwargs.get("name"))
            default = kwargs.get("default_value", kwargs.get("default"))
            return {"type": "arg", "name": name, "default": self._resolve(default)}
        if short == "IncludeLaunchDescription":
            source_value = args[0] if args else kwargs.get("launch_description_source")
            return {"type": "include", "file": source_value, "args": []}
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
                "env": self._convert_env(kwargs.get("additional_env", kwargs.get("env")))
            }
        if short in {"LaunchConfiguration", "TextSubstitution", "EnvironmentVariable",
                     "FindPackageShare", "ThisLaunchFileDir"}:
            return self._symbolic(qname, args, kwargs)
        if short in {"PythonLaunchDescriptionSource", "XMLLaunchDescriptionSource",
                     "YAMLLaunchDescriptionSource"}:
            path_value = args[0] if args else kwargs.get("location")
            return {"type": "launch_source", "source_type": short, "path": path_value}
        return self._symbolic(qname, args, kwargs)

    def _symbolic(self, qname, args, kwargs):
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
        if isinstance(value, Node):
            return Node(
                name=self._resolve(value.name),
                package=self._resolve(value.package),
                exec=self._resolve(value.exec),
                namespace=self._resolve(value.namespace),
                remappings=self._convert_remaps(self._resolve(value.remappings) or []),
                params=self._convert_params(self._resolve(value.params) or []),
                args=self._resolve(value.args),
            )
        if isinstance(value, dict):
            if value.get("type") == "launch_description":
                return {"type": "launch_description",
                        "actions": [self._resolve(a) for a in value.get("actions", [])]}
            if value.get("type") in {"arg", "include", "set_env", "unset_env",
                                     "executable", "add_action", "launch_source"}:
                return {k: self._resolve(v) for k, v in value.items()}
            return {self._resolve(k): self._resolve(v) for k, v in value.items()}
        return value

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
            elif kind == "return":
                self._consume_return(stmt[1])
            elif isinstance(stmt, dict) and stmt.get("type") == "add_action":
                target = stmt["target"]
                action = self._resolve(stmt["action"])
                self.launch_descriptions.setdefault(target, []).append(action)

    def _consume_return(self, value):
        resolved = self._resolve(value)
        if isinstance(resolved, dict) and resolved.get("type") == "launch_description":
            self._consume_actions(resolved["actions"])
        elif isinstance(resolved, str) and resolved in self.launch_descriptions:
            self._consume_actions(self.launch_descriptions[resolved])
        elif isinstance(value, dict) and value.get("type") == "var":
            name = value["name"]
            if name in self.launch_descriptions:
                self._consume_actions(self.launch_descriptions[name])

    def _consume_actions(self, actions):
        for action in actions:
            if isinstance(action, Node):
                self.arch.add_node(action)
            elif isinstance(action, dict):
                kind = action.get("type")
                if kind == "arg":
                    self.arch.args[action["name"]] = action.get("default")
                elif kind == "include":
                    file_value = self._resolve(action.get("file"))
                    if isinstance(file_value, dict) and file_value.get("type") == "launch_source":
                        file_value = file_value.get("path")
                    self.arch.includes.append(file_value)
                elif kind == "set_env":
                    self.arch.env[action["name"]] = action.get("value")
                elif kind == "unset_env":
                    self.arch.unset_env.append(action["name"])
                elif kind == "executable":
                    self.arch.executables.append(action)

    def _is_action(self, value):
        return isinstance(value, Node) or (
            isinstance(value, dict) and
            value.get("type") in {"arg", "include", "set_env", "unset_env", "executable"}
        )

    def _convert_remaps(self, remaps):
        result = []
        for item in remaps:
            item = self._resolve(item)
            if isinstance(item, Remapping):
                result.append(item)
            elif isinstance(item, tuple) and len(item) == 2:
                result.append(Remapping(src=item[0], dst=item[1]))
            elif isinstance(item, list) and len(item) == 2:
                result.append(Remapping(src=item[0], dst=item[1]))
        return result

    def _convert_params(self, params_raw):
        params = []
        for item in params_raw:
            item = self._resolve(item)
            if isinstance(item, dict):
                for key, value in item.items():
                    params.append(Param(str(key), value))
        return params

    def _convert_env(self, env_value):
        env_value = self._resolve(env_value)
        if isinstance(env_value, dict):
            return [{"type": "env", "name": str(k), "value": v} for k, v in env_value.items()]
        return []