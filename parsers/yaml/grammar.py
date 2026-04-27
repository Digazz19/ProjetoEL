grammarYAML = r"""
start: _NL* yaml_header* launch _NL*

yaml_header: (YAML_DIRECTIVE | YAML_SEP) _NL*

launch: "launch" ":" _NL _INDENT element* _DEDENT

element: "-" node
       | "-" include
       | "-" group
       | "-" arg
       | "-" let
       | "-" executable
       | "-" set_env
       | "-" unset_env

node: "node" ":" _NL _INDENT node_content* _DEDENT
node_content: attribute | remap | param | env

include: "include" ":" _NL _INDENT include_content* _DEDENT
include_content: attribute | args

group: "group" ":" _NL _INDENT element* _DEDENT

arg: "arg" ":" _NL _INDENT attribute* _DEDENT
let: "let" ":" _NL _INDENT attribute* _DEDENT
set_env: "set_env" ":" _NL _INDENT attribute* _DEDENT
unset_env: "unset_env" ":" _NL _INDENT attribute* _DEDENT

executable: "executable" ":" _NL _INDENT exec_content* _DEDENT
exec_content: attribute | env

param: "param" ":" _NL _INDENT dict_item* _DEDENT
remap: "remap" ":" _NL _INDENT dict_item* _DEDENT
env: "env" ":" _NL _INDENT dict_item* _DEDENT
args: "arg" ":" _NL _INDENT dict_item* _DEDENT

dict_item: "-" attribute (_INDENT attribute* _DEDENT)?

attribute: NAME ":" STRING _NL

YAML_DIRECTIVE: /%[^\n]*/
YAML_SEP: /---/
COMMENT: /#[^\n]*/

NAME: /[a-zA-Z_][a-zA-Z0-9_-]*/
STRING: ESCAPED_STRING | /[a-zA-Z0-9_\-\.\/]+/

_NL: /(\r?\n[\t ]*)+/

%declare _INDENT _DEDENT
%import common.ESCAPED_STRING
%import common.WS_INLINE

%ignore WS_INLINE
%ignore COMMENT
"""