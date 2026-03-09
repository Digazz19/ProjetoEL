class ArchitectureROS:

    def __init__(self):
        self.nodes = {}
        self.args = {}
        self.lets = {}
        self.includes = []
        self.executables = []
        self.env = {}
        self.unset_env = []

    def add_node(self, node):
        self.nodes[node.name] = node


class Node:

    def __init__(self, name, package, exec,
                 namespace=None,
                 remappings=None,
                 params=None,
                 args=None):

        self.name = name
        self.package = package
        self.exec = exec
        self.namespace = namespace
        self.remappings = remappings or []
        self.params = params or []
        self.args = args

    def __repr__(self):
        return f"""
Node(
 name={self.name},
 pkg={self.package},
 exec={self.exec},
 namespace={self.namespace},
 remaps={self.remappings},
 params={self.params},
 args={self.args}
)
"""


class Param:

    def __init__(self, name, value):
        self.name = name
        self.value = value

    def __repr__(self):
        return f"{self.name}={self.value}"