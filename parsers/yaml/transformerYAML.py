from models.architectureROS import ArchitectureROS, Node, Param
from lark import Transformer

class LaunchYAMLTransformer(Transformer):

    def start(self, items):
        # Find the ArchitectureROS object, ignoring any leading/trailing _NL tokens
        for item in items:
            if isinstance(item, ArchitectureROS):
                return item
        return items[-1]

    def launch(self, items):
        arch = ArchitectureROS()

        def process(item):
            if isinstance(item, Node):
                arch.add_node(item)
            elif isinstance(item, dict):
                t = item.get("type")
                if t == "arg":
                    arch.args[item["name"]] = item.get("default")
                elif t == "let":
                    arch.lets[item["name"]] = item.get("value")
                elif t == "include":
                    arch.includes.append(item["file"])
                elif t == "set_env":
                    arch.env[item["name"]] = item.get("value")
                elif t == "unset_env":
                    arch.unset_env.append(item["name"])
                elif t == "executable":
                    arch.executables.append(item)
            elif isinstance(item, list):
                # Now that lists (groups) make it here, process their contents!
                for sub in item:
                    process(sub)

        for item in items:
            process(item)

        return arch

    def element(self, items): 
        for item in items:
            # Added `list` here so groups don't get dropped!
            if isinstance(item, (dict, Node, list)): return item

    def node_content(self, items): 
        for item in items:
            if isinstance(item, (dict, tuple)): return item

    def include_content(self, items): 
        for item in items:
            if isinstance(item, (dict, tuple)): return item

    def exec_content(self, items): 
        for item in items:
            if isinstance(item, (dict, tuple)): return item

    def node(self, items):
        attrs = {}
        remaps = []
        params = []
        for item in items:
            if isinstance(item, dict):
                if item["type"] == "remap":
                    remaps.extend(item["data"])
                elif item["type"] == "param":
                    params.extend(item["data"])
            elif isinstance(item, tuple):
                attrs[item[0]] = item[1]

        return self._build_node(attrs, remaps, params)

    def include(self, items):
        attrs = {}
        args = []
        for item in items:
            if isinstance(item, dict) and item.get("type") == "args":
                args.extend(item["data"])
            elif isinstance(item, tuple):
                attrs[item[0]] = item[1]

        return {"type": "include", "file": attrs.get("file"), "args": args}

    def group(self, items):
        return [i for i in items if isinstance(i, (dict, Node, list))]

    def arg(self, items):
        attrs = dict([i for i in items if isinstance(i, tuple)])
        return {"type": "arg", "name": attrs.get("name"), "default": attrs.get("default", attrs.get("value"))}

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
        params = [Param(dict(i).get("name"), dict(i).get("value")) for i in valid]
        return {"type": "param", "data": params}

    def remap(self, items):
        valid = [i for i in items if isinstance(i, list)]
        remaps = [(dict(i).get("from"), dict(i).get("to")) for i in valid]
        return {"type": "remap", "data": remaps}

    def env(self, items):
        valid = [i for i in items if isinstance(i, list)]
        envs = [{"type": "env", "name": dict(i).get("name"), "value": dict(i).get("value")} for i in valid]
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
        # remove quotes from strings if they exist
        if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
            value = value[1:-1]
        return (key, value)

    def _build_node(self, attrs, remaps, params):
        return Node(
            name=attrs.get("name"),
            package=attrs.get("pkg"),
            exec=attrs.get("exec"),
            namespace=attrs.get("namespace"),
            remappings=remaps,
            params=params,
            args=attrs.get("args", attrs.get("ros_args")) 
        )