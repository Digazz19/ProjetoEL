from models.architectureROS import ArchitectureROS, Node, Param
from lark import Transformer

class LaunchXMLTransformer(Transformer):

    def start(self, items):
        return items[0]

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
                for sub in item:
                    process(sub)

        for item in items:
            process(item)

        return arch
    
    def element(self, items):
        return items[0]

    def node_content(self, items):
        return items[0]

    def node(self, items):
        return items[0]

    def empty_node(self, items):
        attrs = dict(items)
        return self._build_node(attrs, [], [])

    def full_node(self, items):
        attrs = {}
        remaps = []
        params = []
        for item in items:
            if isinstance(item, dict):
                if item["type"] == "remap":
                    remaps.append((item["from"], item["to"]))
                elif item["type"] == "param":
                    params.append(
                        Param(item["name"], item["value"])
                    )
            elif isinstance(item, tuple):
                attrs[item[0]] = item[1]

        return self._build_node(attrs, remaps, params)

    def remap(self, items):
        attrs = dict(items)
        return {
            "type": "remap",
            "from": attrs.get("from"),
            "to": attrs.get("to")
        }

    def param(self, items):
        attrs = dict(items)
        return {
            "type": "param",
            "name": attrs.get("name"),
            "value": attrs.get("value")
        }

    def let(self, items):
        attrs = dict(items)
        return {
            "type": "let",
            "name": attrs.get("name"),
            "value": attrs.get("value")
        }
    
    def executable(self, items):
        attrs = {}
        envs = []
        for item in items:
            if isinstance(item, dict) and item.get("type") == "env":
                envs.append(item)
            elif isinstance(item, tuple):
                attrs[item[0]] = item[1]

        return {
            "type": "executable",
            "cmd": attrs.get("cmd"),
            "cwd": attrs.get("cwd"),
            "env": envs
        }
    
    def env(self, items):
        attrs = dict(items)
        return {
            "type": "env",
            "name": attrs.get("name"),
            "value": attrs.get("value")
        }
    
    def set_env(self, items):
        attrs = dict(items)
        return {
            "type": "set_env",
            "name": attrs.get("name"),
            "value": attrs.get("value")
        }
    
    def unset_env(self, items):
        attrs = dict(items)
        return {
            "type": "unset_env",
            "name": attrs.get("name")
        }

    def include(self, items):
        attrs = {}
        args = []
        for item in items:
            if isinstance(item, dict) and item.get("type") == "arg":
                args.append(item)
            elif isinstance(item, tuple):
                attrs[item[0]] = item[1]

        return {
            "type": "include",
            "file": attrs.get("file"),
            "args": args
        }

    def arg(self, items):
        attrs = dict(items)
        return {
            "type": "arg",
            "name": attrs.get("name"),
            "default": attrs.get("default")
        }


    def group(self, items):
        return items

    def attribute(self, items):
        key = str(items[0])
        value = items[1][1:-1]
        return (key, value)


    def _build_node(self, attrs, remaps, params):
        return Node(
            name=attrs.get("name"),
            package=attrs.get("pkg"),
            exec=attrs.get("exec"),
            namespace=attrs.get("namespace"),
            remappings=remaps,
            params=params
        )