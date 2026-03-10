import ast

from .visitor import PythonLaunchVisitor

# constrói a AST usando ast.parse() ; cria um visitor (PythonLaunchVisitor) 
# percorre a árvore sintática com esse visitor e devolve a arquitetura extraída.

class PythonLaunchParser:

    def parse(self, file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()

        tree = ast.parse(text, filename=file_path)
        visitor = PythonLaunchVisitor()
        visitor.visit(tree)

        return tree, visitor.architecture
