import ast

from models.architectureROS import ArchitectureROS, Node, Param


class PythonLaunchVisitor(ast.NodeVisitor):
    """
    Extração estática, baseada em padrões comuns de launch files ROS2 em Python.

    Cobre sobretudo:
      - generate_launch_description()
      - LaunchDescription([...])
      - ld = LaunchDescription(); ld.add_action(...); return ld
      - Node(...)
      - DeclareLaunchArgument(...)
      - IncludeLaunchDescription(...)
      - SetEnvironmentVariable(...)
      - UnsetEnvironmentVariable(...)
      - ExecuteProcess(...)

    Não executa o script. Quando não consegue resolver algo dinamicamente,
    guarda uma representação simbólica simples com ast.unparse(...).
    """

    def __init__(self):
        self.architecture = ArchitectureROS()

        self.aliases = {
            "Node": "Node",
            "LaunchDescription": "LaunchDescription",
            "DeclareLaunchArgument": "DeclareLaunchArgument",
            "IncludeLaunchDescription": "IncludeLaunchDescription",
            "SetEnvironmentVariable": "SetEnvironmentVariable",
            "UnsetEnvironmentVariable": "UnsetEnvironmentVariable",
            "ExecuteProcess": "ExecuteProcess",
            "LaunchConfiguration": "LaunchConfiguration",
            "PythonLaunchDescriptionSource": "PythonLaunchDescriptionSource",
            "XMLLaunchDescriptionSource": "XMLLaunchDescriptionSource",
            "YAMLLaunchDescriptionSource": "YAMLLaunchDescriptionSource",
            "PathJoinSubstitution": "PathJoinSubstitution",
            "TextSubstitution": "TextSubstitution",
            "EnvironmentVariable": "EnvironmentVariable",
            "FindPackageShare": "FindPackageShare",
            "ThisLaunchFileDir": "ThisLaunchFileDir",
        }

        self.env_stack = []
        self.launch_description_stack = []
        # Evita processar a mesma LaunchDescription duas vezes.
        self.processed_launch_descriptions = set()

    # =========================
    # Visitor principal
    # =========================

    # Métodos visit_* chamados automaticamente ao percorrer a AST.
    # Tratam imports e a função principal generate_launch_description().

    def visit_ImportFrom(self, node):
        for alias in node.names:
            self.aliases[alias.asname or alias.name] = alias.name

    def visit_Import(self, node):
        for alias in node.names:
            imported = alias.name.split(".")[-1]
            self.aliases[alias.asname or imported] = imported

    def visit_FunctionDef(self, node):
        if node.name != "generate_launch_description":
            return

        self.env_stack.append({})
        self.launch_description_stack.append({})

        for stmt in node.body:
            self._process_statement(stmt)

        self.launch_description_stack.pop()
        self.env_stack.pop()

    # =========================
    # Processamento por statement
    # =========================

    # Processa instruções do corpo da função e encaminha cada uma 
    # para o tratamento adequado consoante o tipo de statement.

    def _process_statement(self, stmt):
        if isinstance(stmt, ast.Assign):
            self._handle_assign(stmt)
            return

        if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
            value = self._parse_ast_value(stmt.value) if stmt.value is not None else None
            self._set_env(stmt.target.id, value)
            return

        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
            self._handle_expr_call(stmt.value)
            return

        if isinstance(stmt, ast.Return):
            self._handle_return(stmt)
            return

        if isinstance(stmt, ast.If):
            # Análise conservadora: percorre ambos os ramos, se existirem.
            for inner in stmt.body:
                self._process_statement(inner)
            for inner in stmt.orelse:
                self._process_statement(inner)
            return

        if isinstance(stmt, (ast.For, ast.While, ast.With, ast.Try)):
            # Limitação assumida: recolha best-effort dos blocos internos.
            for body_stmt in getattr(stmt, "body", []):
                self._process_statement(body_stmt)
            for orelse_stmt in getattr(stmt, "orelse", []):
                self._process_statement(orelse_stmt)
            for final_stmt in getattr(stmt, "finalbody", []):
                self._process_statement(final_stmt)
            for handler in getattr(stmt, "handlers", []):
                for handler_stmt in getattr(handler, "body", []):
                    self._process_statement(handler_stmt)

    # Trata atribuições normais, incluindo variáveis simples e LaunchDescriptions guardadas em variáveis.
    def _handle_assign(self, stmt):
        value = stmt.value

        if isinstance(value, ast.Call) and self._canonical_name(value.func) == "LaunchDescription":
            actions = self._extract_launch_description_actions(value)
            for target in stmt.targets:
                if isinstance(target, ast.Name):
                    self._set_launch_description(target.id, actions)
            return

        parsed_value = self._parse_ast_value(value)
        for target in stmt.targets:
            if isinstance(target, ast.Name):
                self._set_env(target.id, parsed_value)

    # Trata chamadas soltas como ld.add_action(...), associando a ação à LaunchDescription correta.
    def _handle_expr_call(self, call_node):
        # Suporte a: ld.add_action(Node(...))
        if isinstance(call_node.func, ast.Attribute) and call_node.func.attr == "add_action":
            base = call_node.func.value
            if isinstance(base, ast.Name) and call_node.args:
                action = self._parse_action(call_node.args[0])
                if action is not None:
                    self._append_launch_description_action(base.id, action)

    def _handle_return(self, stmt):
        value = stmt.value
        if value is None:
            return

        if isinstance(value, ast.Call) and self._canonical_name(value.func) == "LaunchDescription":
            actions = self._extract_launch_description_actions(value)
            self._consume_actions(actions)
            return

        if isinstance(value, ast.Name):
            actions = self._get_launch_description(value.id)
            if actions is not None and value.id not in self.processed_launch_descriptions:
                self._consume_actions(actions)
                self.processed_launch_descriptions.add(value.id)

    # =========================
    # Extração de ações
    # =========================

    # Extrai ações ROS da LaunchDescription e converte-as
    # para a representação intermédia usada no modelo arquitetural.

    def _extract_launch_description_actions(self, call_node):
        if not call_node.args:
            return []

        first_arg = call_node.args[0]
        if isinstance(first_arg, (ast.List, ast.Tuple)):
            actions = []
            for elt in first_arg.elts:
                action = self._parse_action(elt)
                if action is not None:
                    actions.append(action)
            return actions

        resolved = self._parse_ast_value(first_arg)
        if isinstance(resolved, list):
            return [a for a in resolved if a is not None]

        return []

    def _parse_action(self, node):
        resolved = self._parse_ast_value(node)

        if isinstance(resolved, Node):
            return resolved

        if isinstance(resolved, dict) and resolved.get("type") in {
            "arg",
            "include",
            "set_env",
            "unset_env",
            "executable",
        }:
            return resolved

        return None

    def _consume_actions(self, actions):
        for action in actions:
            if isinstance(action, Node):
                self.architecture.add_node(action)
            elif isinstance(action, dict):
                kind = action.get("type")
                if kind == "arg":
                    self.architecture.args[action["name"]] = action.get("default")
                elif kind == "include":
                    self.architecture.includes.append(action.get("file"))
                elif kind == "set_env":
                    self.architecture.env[action["name"]] = action.get("value")
                elif kind == "unset_env":
                    self.architecture.unset_env.append(action["name"])
                elif kind == "executable":
                    self.architecture.executables.append(action)

    # =========================
    # Conversão AST -> valores
    # =========================

    # Converte nós da AST em valores Python, objetos do modelo
    # ou representações simbólicas quando não é possível resolver tudo.

    def _parse_ast_value(self, node):
        if node is None:
            return None

        if isinstance(node, ast.Constant):
            return node.value

        if isinstance(node, ast.List):
            return [self._parse_ast_value(elt) for elt in node.elts]

        if isinstance(node, ast.Tuple):
            return tuple(self._parse_ast_value(elt) for elt in node.elts)

        if isinstance(node, ast.Dict):
            result = {}
            for key_node, value_node in zip(node.keys, node.values):
                if key_node is None:
                    continue
                key = self._parse_ast_value(key_node)
                value = self._parse_ast_value(value_node)
                result[key] = value
            return result

        if isinstance(node, ast.Name):
            resolved = self._get_env(node.id)
            if resolved is not None:
                return resolved
            return self._symbolic(node)

        if isinstance(node, ast.JoinedStr):
            return self._symbolic(node)

        if isinstance(node, ast.Call):
            canonical = self._canonical_name(node.func)

            if canonical == "Node":
                return self._build_node_from_call(node)
            if canonical == "DeclareLaunchArgument":
                return self._build_arg_from_call(node)
            if canonical == "IncludeLaunchDescription":
                return self._build_include_from_call(node)
            if canonical == "SetEnvironmentVariable":
                return self._build_set_env_from_call(node)
            if canonical == "UnsetEnvironmentVariable":
                return self._build_unset_env_from_call(node)
            if canonical == "ExecuteProcess":
                return self._build_executable_from_call(node)
            if canonical == "LaunchDescription":
                return self._extract_launch_description_actions(node)
            if canonical == "LaunchConfiguration":
                return self._symbolic(node)

            if canonical in {
                "PythonLaunchDescriptionSource",
                "XMLLaunchDescriptionSource",
                "YAMLLaunchDescriptionSource",
            }:
                return self._build_launch_source_from_call(node)

            if canonical in {
                "PathJoinSubstitution",
                "TextSubstitution",
                "EnvironmentVariable",
                "FindPackageShare",
                "ThisLaunchFileDir",
            }:
                return self._symbolic(node)
            
            return self._symbolic(node)

        if isinstance(node, ast.Attribute):
            return self._symbolic(node)

        return self._symbolic(node)

    # =========================
    # Builders das ações
    # =========================

    # Constrói objetos ou estruturas intermédias a partir
    # de chamadas ROS reconhecidas no launch file.

    def _build_node_from_call(self, call_node):
        kwargs = self._keyword_args(call_node)

        name = kwargs.get("name")
        package = kwargs.get("package") or kwargs.get("pkg")
        executable = kwargs.get("executable") or kwargs.get("exec")
        namespace = kwargs.get("namespace")

        remappings = self._normalize_remappings(kwargs.get("remappings") or kwargs.get("remaps"))
        params = self._normalize_parameters(kwargs.get("parameters") or kwargs.get("params"))

        if name is None:
            name = f"{package or 'unknown_pkg'}:{executable or 'unknown_exec'}"

        return Node(
            name=name,
            package=package,
            exec=executable,
            namespace=namespace,
            remappings=remappings,
            params=params,
        )

    def _build_launch_source_from_call(self, call_node):
        canonical = self._canonical_name(call_node.func)

        source_value = None
        if call_node.args:
            source_value = self._parse_ast_value(call_node.args[0])

        return {
            "type": "launch_source",
            "source_kind": canonical,
            "file": source_value,
        }

    def _build_arg_from_call(self, call_node):
        kwargs = self._keyword_args(call_node)

        name = None
        if call_node.args:
            name = self._parse_ast_value(call_node.args[0])
        if name is None:
            name = kwargs.get("name")

        return {
            "type": "arg",
            "name": name,
            "default": kwargs.get("default_value") or kwargs.get("default"),
        }

    def _build_include_from_call(self, call_node):
        source = None
        if call_node.args:
            source = self._parse_ast_value(call_node.args[0])

        kwargs = self._keyword_args(call_node)
        source = kwargs.get("launch_description_source", source)

        if isinstance(source, dict) and source.get("type") == "launch_source":
            file_value = source.get("file")
        else:
            file_value = source

        return {
            "type": "include",
            "file": file_value,
            "args": kwargs.get("launch_arguments"),
        }

    def _build_set_env_from_call(self, call_node):
        kwargs = self._keyword_args(call_node)

        name = kwargs.get("name")
        value = kwargs.get("value")

        if len(call_node.args) >= 1 and name is None:
            name = self._parse_ast_value(call_node.args[0])
        if len(call_node.args) >= 2 and value is None:
            value = self._parse_ast_value(call_node.args[1])

        return {
            "type": "set_env",
            "name": name,
            "value": value,
        }

    def _build_unset_env_from_call(self, call_node):
        kwargs = self._keyword_args(call_node)
        name = kwargs.get("name")

        if len(call_node.args) >= 1 and name is None:
            name = self._parse_ast_value(call_node.args[0])

        return {
            "type": "unset_env",
            "name": name,
        }

    def _build_executable_from_call(self, call_node):
        kwargs = self._keyword_args(call_node)
        cmd = kwargs.get("cmd")
        cwd = kwargs.get("cwd")

        env_items = []
        additional_env = kwargs.get("additional_env")
        if isinstance(additional_env, dict):
            for key, value in additional_env.items():
                env_items.append({"type": "env", "name": key, "value": value})

        return {
            "type": "executable",
            "cmd": cmd,
            "cwd": cwd,
            "env": env_items,
        }

    # =========================
    # Normalização de campos
    # =========================

    # Normaliza campos com formatos variáveis, como remappings
    # e parameters, para os formatos esperados pelo modelo.

    def _normalize_remappings(self, value):
        remappings = []

        if isinstance(value, list):
            for item in value:
                if isinstance(item, tuple) and len(item) == 2:
                    remappings.append(item)
                elif isinstance(item, list) and len(item) == 2:
                    remappings.append((item[0], item[1]))

        return remappings

    def _normalize_parameters(self, value):
        params = []

        if isinstance(value, dict):
            for key, param_value in value.items():
                params.append(Param(key, param_value))
            return params

        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    for key, param_value in item.items():
                        params.append(Param(key, param_value))
                else:
                    params.append(Param("__raw__", item))
            return params

        if value is not None:
            params.append(Param("__raw__", value))

        return params

    # =========================
    # Helpers utilitários
    # =========================

    # Funções auxiliares para resolver nomes, argumentos,
    # valores simbólicos e estruturas de contexto internas.

    # Recolhe os argumentos nomeados de uma chamada e resolve os respetivos valores.
    def _keyword_args(self, call_node):
        kwargs = {}
        for keyword in call_node.keywords:
            if keyword.arg is not None:
                kwargs[keyword.arg] = self._parse_ast_value(keyword.value)
        return kwargs

    # Resolve o nome canónico de uma função, tendo em conta possíveis aliases.
    def _canonical_name(self, func_node):
        if isinstance(func_node, ast.Name):
            return self.aliases.get(func_node.id, func_node.id)

        if isinstance(func_node, ast.Attribute):
            return self.aliases.get(func_node.attr, func_node.attr)

        return None

    # Gera uma representação textual de um nó quando não é possível resolvê-lo.
    def _symbolic(self, node):
        try:
            return ast.unparse(node)
        except Exception:
            return f"<unparsed:{type(node).__name__}>"

    # Guarda uma variável no contexto local atual.
    def _set_env(self, name, value):
        if self.env_stack:
            self.env_stack[-1][name] = value

    # Procura uma variável nos contextos locais ativos.
    def _get_env(self, name):
        for scope in reversed(self.env_stack):
            if name in scope:
                return scope[name]
        return None

    # Associa uma lista de ações a uma variável que representa uma LaunchDescription.
    def _set_launch_description(self, name, actions):
        if self.launch_description_stack:
            self.launch_description_stack[-1][name] = actions

    # Obtém as ações associadas a uma LaunchDescription guardada numa variável.
    def _get_launch_description(self, name):
        for scope in reversed(self.launch_description_stack):
            if name in scope:
                return scope[name]
        return None

    # Adiciona uma ação a uma LaunchDescription já registada.
    def _append_launch_description_action(self, name, action):
        for scope in reversed(self.launch_description_stack):
            if name in scope:
                scope[name].append(action)
                return