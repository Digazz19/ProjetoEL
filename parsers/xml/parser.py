from lark import Lark
from .grammar import grammarXML
from .transformerXML import LaunchXMLTransformer


class XMLLaunchParser:

    def __init__(self):
        self.parser = Lark(grammarXML, start="start")

    def parse(self, file_path):
        with open(file_path) as f:
            text = f.read()

        tree = self.parser.parse(text)
        transformer = LaunchXMLTransformer()
        architecture = transformer.transform(tree)

        return tree, architecture