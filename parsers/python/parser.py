from lark import Lark
from lark.indenter import PythonIndenter

from .grammar import grammarPython
from .transformerPython import LaunchPythonTransformer

class PythonLaunchParser:
    def __init__(self):
        self.parser = Lark(
            grammarPython,
            parser="lalr",
            postlex=PythonIndenter(),
            start="start",
        )

    def parse(self, file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()

        if not text.endswith("\n"):
            text += "\n"

        tree = self.parser.parse(text)
        transformer = LaunchPythonTransformer()
        architecture = transformer.transform(tree)
        return tree, architecture
