"""
parsers/xml/parser.py — Layer 2
"""

from lark import Lark
from .grammar import grammarXML
from .transformerXML import LaunchXMLTransformer


class XMLLaunchParser:
    def __init__(self):
        self.parser = Lark(grammarXML, parser="earley", start="start")

    def parse(self, file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        tree = self.parser.parse(text)
        transformer = LaunchXMLTransformer(file_path)
        launch_description = transformer.transform(tree)
        return tree, launch_description