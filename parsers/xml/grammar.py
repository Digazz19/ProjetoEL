grammarXML = r"""
start: launch

launch: "<launch>" element* "</launch>"

element: node
       | include
       | group
       | arg
       | let
       | executable
       | set_env
       | unset_env

node: empty_node
    | full_node

empty_node: "<node" attribute+ "/>"

full_node: "<node" attribute+ ">" node_content* "</node>"

node_content: remap
            | param
            | env

include: "<include" attribute+ ">" arg* "</include>"
       | "<include" attribute+ "/>"

group: "<group" attribute* ">" element* "</group>"

arg: "<arg" attribute+ "/>"

let: "<let" attribute+ "/>"

executable: "<executable" attribute+ ">" env* "</executable>"
          | "<executable" attribute+ "/>"

param: "<param" attribute+ ">" param* "</param>"
     | "<param" attribute+ "/>"

remap: "<remap" attribute+ "/>"

env: "<env" attribute+ "/>"

set_env: "<set_env" attribute+ "/>"

unset_env: "<unset_env" attribute+ "/>"

attribute: NAME "=" STRING

NAME: /[a-zA-Z_][a-zA-Z0-9_-]*/
STRING: ESCAPED_STRING

COMMENT: /<!--(.|\n)*?-->/
XMLDECL: /<\?xml.*?\?>/

%import common.ESCAPED_STRING
%import common.WS

%ignore WS
%ignore COMMENT
%ignore XMLDECL
"""