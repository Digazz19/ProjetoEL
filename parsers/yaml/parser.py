"""
parsers/yaml/parser.py — Layer 2
"""
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
    tab_len = 2


class YAMLLaunchParser:
    def __init__(self):
        self.parser = Lark(grammarYAML, parser='lalr', start="start", postlex=YamlIndenter())

    def parse(self, file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()

        text = text.replace('\r\n', '\n').replace('\r', '\n')

        if not text.endswith('\n'):
            text += '\n'

        tree = self.parser.parse(text)
        transformer = LaunchYAMLTransformer(file_path)
        launch_description = transformer.transform(tree)
        return tree, launch_description