grammarPython = r'''
start: stmt*

stmt: import_stmt
    | funcdef
    | _NEWLINE

import_stmt: "from" dotted_name "import" import_list _NEWLINE
           | "import" import_list _NEWLINE

import_list: import_item ("," import_item)*
import_item: NAME ["as" NAME]
dotted_name: NAME ("." NAME)*

funcdef: "def" "generate_launch_description" "(" ")" ":" suite
suite: _NEWLINE _INDENT func_stmt+ _DEDENT

func_stmt: assign_stmt
         | expr_stmt
         | return_stmt
         | _NEWLINE

assign_stmt: NAME "=" expr _NEWLINE
expr_stmt: method_call _NEWLINE
return_stmt: "return" expr _NEWLINE
method_call: NAME "." "add_action" "(" expr ")"

?expr: launch_description
     | call
     | list
     | tuple
     | dict
     | atom

launch_description: "LaunchDescription" "(" [expr] ")"
call: qualified_name "(" [arguments] ")"

qualified_name: NAME ("." NAME)*
arguments: argument ("," argument)* [","]
?argument: NAME "=" expr   -> kw_argument
         | expr             -> pos_argument

list : "[" [expr ("," expr)* [","]] "]"
tuple: "(" [expr ("," expr)+ [","]] ")"
dict : "{" [dict_item ("," dict_item)* [","]] "}"
dict_item: expr ":" expr

?atom: STRING           -> string
     | SIGNED_NUMBER    -> number
     | "True"          -> true
     | "False"         -> false
     | "None"          -> none
     | NAME             -> var

%import common.CNAME -> NAME
%import common.ESCAPED_STRING -> STRING
%import common.SIGNED_NUMBER
%import common.WS_INLINE
_NEWLINE: /(\r?\n[\t ]*)+/
%declare _INDENT _DEDENT

%ignore WS_INLINE
%ignore /#[^\n]*/
'''
