import os

_lark_path = os.path.join(os.path.dirname(__file__), 'grammar_python.lark')
with open(_lark_path) as _f:
    grammarPython = _f.read()