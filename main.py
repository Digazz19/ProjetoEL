from parsers.xml.parser import XMLLaunchParser
from parsers.yaml.parser import YAMLLaunchParser

def print_architecture(architecture, name=""):
    print(f"\n=== ARQUITETURA EXTRAÍDA ({name}) ===\n")
    for node in architecture.nodes.values():
        print(node)

    print("\nARGS:", architecture.args)
    print("LETS:", architecture.lets)
    print("INCLUDES:", architecture.includes)
    print("ENV:", architecture.env)
    print("UNSET_ENV:", architecture.unset_env)
    print("EXECUTABLES:", architecture.executables)

# TEST XML
xml_parser = XMLLaunchParser()
xml_tree, xml_architecture = xml_parser.parse("examples/test.xml")
print_architecture(xml_architecture, "XML")
print("\n=== PARSE TREE ===\n")
print(xml_tree.pretty())

# TEST YAML
##yaml_parser = YAMLLaunchParser()
##yaml_tree, yaml_architecture = yaml_parser.parse("examples/test.yaml")
##print_architecture(yaml_architecture, "YAML")
##print("\n=== PARSE TREE ===\n")
##print(yaml_tree.pretty())