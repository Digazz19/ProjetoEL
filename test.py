from lark import Lark, Transformer

class ArchitectureROS:
    def __init__(self):
        self.nodes = {}

    def add_node(self, node):
        self.nodes[node.name] = node


class Node:
    def __init__(self, name, package, exec, namespace=None, remappings=None):
        self.name = name
        self.package = package
        self.exec = exec
        self.namespace = namespace
        self.remappings = remappings

    def __repr__(self):
        return f"Node(name={self.name}, pkg={self.package}, exec={self.exec}, ns={self.namespace}, remap={self.remappings})"


# ==============================
# Gramática
# ==============================

grammarXML = r"""
start: launch

launch: "<launch>" node* "</launch>"

node: empty_node
    | full_node

empty_node: "<node" attribute+ "/>"

full_node: "<node" attribute+ ">" remap* "</node>"

remap: "<remap" attribute+ "/>"

attribute: NAME "=" STRING

NAME: /[a-zA-Z_][a-zA-Z0-9_]*/
STRING: ESCAPED_STRING

%import common.ESCAPED_STRING
%import common.WS
%ignore WS
"""

class LaunchTransformer(Transformer):\

    def start(self, items):
        return items[0]

    def launch(self, items):
        arch = ArchitectureROS()
        for node in items:
            arch.add_node(node)
        return arch

    def node(self, items):
        return items[0]

    def empty_node(self, items):
        attrs = dict(items)
        return self._build_node(attrs, [])

    def full_node(self, items):
        attrs = {}
        remaps = []

        for item in items:
            if isinstance(item, dict) and item.get("type") == "remap":
                remaps.append((item["from"], item["to"]))
            else:
                attrs[item[0]] = item[1]

        return self._build_node(attrs, remaps)

    def remap(self, items):
        attrs = dict(items)
        return {
            "type": "remap",
            "from": attrs.get("from"),
            "to": attrs.get("to")
        }

    def attribute(self, items):
        key = str(items[0])
        value = items[1][1:-1]
        return (key, value)

    def _build_node(self, attrs, remaps):
        return Node(
            name=attrs.get("name"),
            package=attrs.get("pkg"),
            exec=attrs.get("exec"),
            namespace=attrs.get("namespace"),
            remappings=remaps
        )


parser = Lark(grammarXML, start="start")

with open("examples/test.xml", "r") as f:
    text = f.read()

tree = parser.parse(text)
print(tree.pretty())

transformer = LaunchTransformer()
architecture = transformer.transform(tree)


for node_name, node in architecture.nodes.items():
    print(node)
