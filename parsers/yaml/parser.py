from lark import Lark
from lark.indenter import Indenter
from .grammar import grammarYAML
from .transformerYAML import LaunchYAMLTransformer

class YamlIndenter(Indenter):
    NL_type = '_NL'
    OPEN_PAREN_types = []
    CLOSE_PAREN_types = []
    INDENT_type = '_INDENT'
    DEDENT_type = '_DEDENT'
    tab_len = 2  # YAML normally uses 2 spaces per indentation level

class YAMLLaunchParser:
    def __init__(self):
        # We pass the custom indenter into the 'postlex' parameter
        self.parser = Lark(grammarYAML, parser='lalr', start="start", postlex=YamlIndenter())

    def parse(self, file_path):
        with open(file_path) as f:
            text = f.read()
            
        # Lark's indenter requires a final newline to correctly trigger _DEDENT at the end of the file
        if not text.endswith('\n'):
            text += '\n'

        tree = self.parser.parse(text)
        transformer = LaunchYAMLTransformer()
        architecture = transformer.transform(tree)

        return tree, architecture