from parsers.xml.parser import XMLLaunchParser

parser = XMLLaunchParser()

tree, architecture = parser.parse("examples/example.launch.xml")

print("\n=== PARSE TREE ===\n")
print(tree.pretty())

print("\n=== ARQUITETURA EXTRAÍDA ===\n")

for node in architecture.nodes.values():
    print(node)

print("\nARGS:", architecture.args)
print("LETS:", architecture.lets)
print("INCLUDES:", architecture.includes)
print("ENV:", architecture.env)
print("UNSET_ENV:", architecture.unset_env)
print("EXECUTABLES:", architecture.executables)