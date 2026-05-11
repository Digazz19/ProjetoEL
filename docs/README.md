# Estratégia de Extracção — ProjetoEL Layer 2

Este documento detalha a estratégia usada para extrair e guardar cada tipo de informação presente nos launch files ROS2 (XML, YAML e Python), produzindo uma representação intermédia **Layer 2** conforme a especificação HAROS.

---

## 📋 Índice

1. [Visão Geral da Pipeline](#1-visão-geral-da-pipeline)
2. [Como os Argumentos são Guardados](#2-como-os-argumentos-são-guardados)
3. [Como os Nodes são Guardados](#3-como-os-nodes-são-guardados)
4. [Como os Includes são Guardados](#4-como-os-includes-são-guardados)
5. [Como os Grupos são Guardados](#5-como-os-grupos-são-guardados)
6. [Como os Namespaces são Guardados](#6-como-os-namespaces-são-guardados)
7. [Como as Condições são Guardadas](#7-como-as-condições-são-guardadas)
8. [Como os ComposableNodes são Guardados](#8-como-os-composablenodes-são-guardados)
9. [Como os OpaqueFunction e For Loops são Tratados](#9-como-os-opaquefunction-e-for-loops-são-tratados)
10. [Como os Valores Simbólicos são Representados](#10-como-os-valores-simbólicos-são-representados)
11. [Como a Proveniência é Guardada](#11-como-a-proveniência-é-guardada)
12. [Como os IDs são Gerados](#12-como-os-ids-são-gerados)
13. [Casos Especiais e Limitações](#13-casos-especiais-e-limitações)

---

## 1. Visão Geral da Pipeline

Cada launch file passa por 4 etapas:

```
Ficheiro fonte (.xml / .yaml / .py)
        │
        ▼  parser.py
   Lark parse → Parse Tree (AST)
        │
        ▼  transformer*.py
   Transformer (bottom-up) → Modelo intermédio Layer 2
        │
        ▼  layer2.py
   LaunchDescription (em memória)
        │
        ├──► print_summary()  →  Output legível no terminal
        └──► to_json()        →  JSON guardado em output/
```

O transformer percorre a árvore **bottom-up** — os nós folha são processados primeiro, e os resultados sobem até ao topo. Isto significa que quando o transformer processa um `Node(...)`, já tem os valores dos seus argumentos resolvidos.

---

## 2. Como os Argumentos são Guardados

### Formato Layer 2

```json
{
  "id": "la:file_spawn:c055eba9#0",
  "action_type": "declare_argument",
  "name": "use_sim_time",
  "default_value": {"type": "literal", "value": "True"},
  "description": "Flag to enable use_sim_time",
  "choices": null,
  "provenance": { ... }
}
```

### Em Python

O transformer reconhece `DeclareLaunchArgument(...)` no método `_specialize_call`:

```python
if short == "DeclareLaunchArgument":
    name = self._resolve(args[0]) if args else self._resolve(kwargs.get("name"))
    default = kwargs.get("default_value", kwargs.get("default"))
    desc = kwargs.get("description")
    choices = kwargs.get("choices")
    return {"type": "arg", "name": name, "default": ..., "description": ..., "choices": ...}
```

Este dict intermédio é depois convertido num `DeclareArgumentAction` em `_consume_actions`.

### Caso especial: args declarados mas não adicionados ao LaunchDescription

No `opaque_multi_nodes_inplace.launch.py`, o arg é declarado mas nunca adicionado ao `ld`:

```python
declared_args = []
declared_args.append(DeclareLaunchArgument("num_node_pairs", default_value="1"))
ld = LaunchDescription()  # vazio — declared_args nunca é adicionado!
```

Para lidar com este caso, o método `_extract_orphan_args` corre no final da transformação e procura args em variáveis de lista que nunca chegaram ao `LaunchDescription`:

```python
def _extract_orphan_args(self):
    for var_name, var_val in self.variables.items():
        if not isinstance(var_val, list): continue
        for item in var_val:
            if item.get("type") == "arg" and item["name"] not in existing_arg_names:
                self._ld.add_action(DeclareArgumentAction(..., confidence=0.8))
```

A `confidence` é `0.8` (em vez de `1.0`) porque o arg não foi explicitamente adicionado ao `LaunchDescription`.

### Em XML

O parser reconhece `<arg name="x" default="y"/>` e o transformer converte directamente:

```python
def arg(self, items):
    attrs = dict(items)
    return {"type": "arg", "name": attrs.get("name"), "default": attrs.get("default"), ...}
```

### Padrão `list.append()`

```python
declared_args.append(DeclareLaunchArgument("x", default_value="1"))
```

A gramática tem uma regra dedicada `list_append_stmt` e o transformer rastreia o append:

```python
def list_append_stmt(self, items):
    return {"type": "list_append", "target": str(items[0]), "item": items[1]}
```

No `_process_function_body`, quando encontra `list_append`, adiciona o item à lista em `self.variables[target]`.

---

## 3. Como os Nodes são Guardados

### Formato Layer 2

```json
{
  "id": "la:file_spawn:c58550db#0",
  "action_type": "node",
  "package": {"type": "literal", "value": "ros_gz_sim"},
  "executable": {"type": "literal", "value": "create"},
  "name": {"type": "literal", "value": "spawn_node"},
  "namespace": null,
  "parameters": {
    "use_sim_time": {"type": "argument_reference", "argument_name": "use_sim_time"}
  },
  "remappings": [
    {"from": "/tf", "to": {"type": "literal", "value": "tf"}}
  ],
  "ros_arguments": ["-x", "$(arg x)", "-y", "$(arg y)"],
  "launch_prefix": null,
  "conditions": [],
  "provenance": { ... }
}
```

### Em Python — `_make_node_action`

O método central que constrói um `NodeAction`:

```python
def _make_node_action(self, node_data: dict, condition: str = None) -> NodeAction:
    # 1. Combinar condições pendentes
    pending = node_data.get("_pending_condition")
    if pending:
        condition = f"({condition}) and ({pending})" if condition else pending

    pkg = node_data.get("package")
    exe = node_data.get("executable")

    # 2. Construir parâmetros como LaunchSubstitution
    params = {}
    for p in node_data.get("params", []):
        if isinstance(p, dict):
            for k, v in p.items():
                params[str(k)] = self._sub(v)  # _sub converte para LaunchSubstitution

    # 3. Construir remappings
    remaps = [Remapping(from_topic=r[0], to_topic=self._sub(r[1])) for r in ...]

    # 4. ros_arguments — converter LaunchConfiguration para $(arg x)
    ros_args = [self._sub(self._resolve(a)).display() for a in raw_args]

    # 5. Gerar ID hash e criar NodeAction
    return NodeAction(
        id=self._id_gen.generate(f"Node(pkg={pkg},exec={exe},name={name})"),
        package=self._sub(pkg),
        executable=self._sub(exe),
        ...
        conditions=cond_list,
        provenance=self._provenance(0.9 if condition else 1.0),
    )
```

### `IfCondition` e `UnlessCondition`

O transformer reconhece `condition=IfCondition(LaunchConfiguration('x'))` no `_specialize_call` via `_condition_expr_to_ir`:

```python
if short == "IfCondition":
    return {"condition": ["eq", ["launch_arg_get", arg_name], "true"]}

if short == "UnlessCondition":
    return {"condition": ["not", ["eq", ["launch_arg_get", arg_name], "true"]]}
```

O kwarg `condition` do `Node` é guardado no `node_raw` e depois aplicado em `_make_node_action`.

### Em XML

```xml
<node pkg="nav2" exec="controller" if="$(var use_sim)"/>
```

O atributo `if` é convertido para IR:

```python
if item.get("if"):
    cond_list.append(_parse_launch_condition_to_ir(item["if"]))
```

---

## 4. Como os Includes são Guardados

### Formato Layer 2

```json
{
  "id": "la:file_spawn:8e31550a#0",
  "action_type": "include",
  "included_launch_id": "launch_desc_file_world_launch_py",
  "argument_mappings": {
    "world": {"type": "argument_reference", "argument_name": "world"}
  },
  "conditions": [],
  "provenance": { ... }
}
```

### Estratégia de resolução do caminho

O `included_launch_id` é gerado a partir do caminho do ficheiro incluído. O problema é que o caminho pode ser:

1. **Literal**: `"sensors.launch.xml"` → ID limpo
2. **Lista com função de runtime**: `[ThisLaunchFileDir(), '/turtlebot3_state_publisher.launch.py']`
3. **`os.path.join(variavel, ...)`**: `os.path.join(pkg_var, 'launch', 'world.launch.py')`

Para os casos 2 e 3, o transformer tenta extrair o **nome do ficheiro** da lista ou string:

```python
if isinstance(file_value, list):
    # Percorrer de trás para a frente e pegar no primeiro elemento com .launch
    for part in reversed(file_value):
        part = self._resolve(part)
        if isinstance(part, str) and '.launch' in part:
            file_str = part.strip('/')
            break
elif isinstance(file_value, str):
    basename = os.path.basename(file_value)
    if ".launch" in basename:
        file_str = basename
```

Isto permite que `[ThisLaunchFileDir(), '/turtlebot3_state_publisher.launch.py']` produza `launch_desc_file_turtlebot3_state_publisher_launch_py`.

### Display legível no terminal

O `_print_action` usa regex para extrair um nome legível do `included_launch_id`:

```python
# Caso simples: launch_desc_file_turtlebot3_state_publisher_launch_py
clean = re.sub(r"^launch_desc_file_", "", inc_id)
clean = re.sub(r"_launch_py$", ".launch.py", clean)
# → turtlebot3_state_publisher.launch.py

# Caso os.path.join: extrair do final do ID
m = re.search(r"_____([a-z][a-z0-9_]+_launch(?:_py|_xml|_yaml)?)__+$", inc_id)
# → slam.launch.py, localization.launch.py, etc.
```

---

## 5. Como os Grupos são Guardados

### Formato Layer 2

```json
{
  "id": "la:file_bringup:abc123#0",
  "action_type": "group",
  "namespace": null,
  "set_parameters": {},
  "children": [
    "la:file_bringup:def456#0",
    "la:file_bringup:111aaa#0"
  ],
  "conditions": [],
  "provenance": { ... }
}
```

A chave é que os **filhos não estão na `launch_sequence` principal** — aparecem no `actions` map mas são acedidos via `group.children`.

### Em XML

O `<group>` é processado em `_process_item`:

```python
elif t == "group":
    group = GroupAction(id=self._id_gen.generate("group"), ...)
    ld.add_action(group)  # adiciona grupo à sequência

    child_ids = []
    for child in item.get("children", []):
        prev_seq = list(ld.launch_sequence)
        self._process_item(ld, child, conditions)  # processa filhos
        new_ids = [aid for aid in ld.launch_sequence if aid not in prev_seq]
        child_ids.extend(new_ids)
        for aid in new_ids:
            ld.launch_sequence.remove(aid)  # ← remove filhos da sequência principal

    group.children = child_ids  # ← atribui ao grupo
```

### Em Python — `GroupAction([...])`

O `GroupAction` Python passa uma lista de acções como argumento posicional:

```python
bringup_cmd_group = GroupAction([
    Node(package='rclcpp_components', ...),
    IncludeLaunchDescription(...),
])
```

O `_specialize_call` reconhece `GroupAction` e guarda as acções filhas:

```python
if short == "GroupAction":
    children = self._resolve(args[0]) if args else self._resolve(kwargs.get("actions", []))
    return {"type": "group_action", "children": children}
```

Em `_consume_actions`, quando encontra `group_action`:

```python
elif t == "group_action":
    group = GroupAction(id=self._id_gen.generate("group_action"), ...)
    self._ld.add_action(group)  # grupo vai para a sequência

    prev_seq = list(self._ld.launch_sequence)
    self._consume_actions(children_items)  # processa filhos
    new_ids = [aid for aid in self._ld.launch_sequence if aid not in prev_seq]

    # Remover filhos da sequência e atribuir ao grupo
    for aid in new_ids:
        self._ld.launch_sequence.remove(aid)
    group.children = new_ids
```

---

## 6. Como os Namespaces são Guardados

### `PushRosNamespace` em Python

```python
PushRosNamespace(namespace)
```

Produz uma `PushNamespaceAction`:

```json
{
  "action_type": "push_namespace",
  "namespace": {"type": "argument_reference", "argument_name": "namespace"},
  "children": [],
  "provenance": { ... }
}
```

O transformer reconhece em `_specialize_call`:

```python
if short == "PushRosNamespace":
    ns = self._resolve(args[0]) if args else self._resolve(kwargs.get("namespace"))
    return {"type": "push_namespace", "namespace": ns}
```

### `<push-ros-namespace>` em XML

```xml
<push-ros-namespace namespace="$(var robot_name)"/>
```

O transformer XML tem um método dedicado:

```python
def push_ros_namespace(self, items):
    attrs = dict(items)
    return {"type": "push_namespace", "namespace": attrs.get("namespace")}
```

### Namespace em GroupAction

Quando um `GroupAction` tem namespace, este é guardado no campo `namespace` do grupo:

```json
{
  "action_type": "group",
  "namespace": {"type": "literal", "value": "/simulation"},
  "children": [...]
}
```

---

## 7. Como as Condições são Guardadas

### Formato IR (Intermediate Representation)

As condições são guardadas como **árvores S-expression**:

```python
# if ROS_DISTRO == 'humble':
[["eq", ["env_get", "ROS_DISTRO"], "humble"]]

# IfCondition(LaunchConfiguration('use_sim'))
[["eq", ["launch_arg_get", "use_sim"], "true"]]

# UnlessCondition(LaunchConfiguration('use_sim'))
[["not", ["eq", ["launch_arg_get", "use_sim"], "true"]]]

# if N<1 or N>5:
[["or", ["lt", ["var_get", "N"], "1"], ["gt", ["var_get", "N"], "5"]]]

# for i in range($(arg num_node_pairs)):
[["truthy", ["var_get", "for i in range($(arg num_node_pairs))"]]]
```

### Condições em Python (`if` statements)

A gramática captura o header do `if` com `IF_HDR.3: /if[^\n:]+:/` e o transformer extrai a condição:

```python
def if_stmt(self, items):
    hdr = str(items[0])  # ex: "if ROS_DISTRO == 'humble':"
    condition = hdr[3:].rstrip(':').strip()  # → "ROS_DISTRO == 'humble'"
    ...
```

A condição string é depois convertida para IR por `_parse_condition_to_ir`:

```python
def _parse_condition_to_ir(s):
    # or / and — split recursivo
    parts = re.split(r'\s+or\s+', s)
    if len(parts) > 1:
        result = _parse_condition_to_ir(parts[0])
        for p in parts[1:]: result = ["or", result, _parse_condition_to_ir(p)]
        return result

    # comparações: ==, !=, <, >, <=, >=
    for op, ir_op in [("==", "eq"), ("!=", "neq"), ("<", "lt"), ...]:
        if op in s:
            left, right = s.split(op, 1)
            return [ir_op, _parse_var_ir(left.strip()), right.strip().strip("'\"")]

    return ["truthy", _parse_var_ir(s)]

def _parse_var_ir(name):
    if name.isupper(): return ["env_get", name]
    if "LaunchConfiguration" in name: return ["launch_arg_get", extracted_name]
    return ["var_get", name]
```

### Condições em XML (`if`/`unless`)

```xml
<node pkg="nav2" exec="controller" if="$(var use_sim)"/>
```

```python
def _parse_launch_condition_to_ir(s):
    m = re.match(r'^\$\((var|arg)\s+(\S+)\)$', s)
    if m:
        return ["eq", ["launch_arg_get", m.group(2)], "true"]
    m = re.match(r'^\$\(env\s+(\S+)\)$', s)
    if m:
        return ["truthy", ["env_get", m.group(1)]]
    return ["truthy", ["var_get", s]]
```

### Condições de `_pending_condition`

Quando um `ComposableNode` está dentro de um `if has_resource(...)`:

```python
if has_resource('packages', 'image_view'):
    composable_nodes.append(ComposableNode(package='image_view', ...))
```

O `_process_if_item` detecta o `list_append` dentro do `if` e marca o node com `_pending_condition`:

```python
elif isinstance(item, dict) and item.get("type") == "list_append":
    value = self._resolve(item["item"])
    if isinstance(value, dict) and value.get("type") == "node_raw":
        value = dict(value)
        value["_pending_condition"] = condition  # ← marca com a condição
    self.variables[target].append(value)
```

Quando o node é processado em `_make_node_action`, a condição pendente é aplicada:

```python
pending = node_data.get("_pending_condition")
if pending:
    condition = f"({condition}) and ({pending})" if condition else pending
```

---

## 8. Como os ComposableNodes são Guardados

### `ComposableNode` — representado como `NodeAction`

A diferença entre `Node` e `ComposableNode` é que o segundo usa `plugin` em vez de `executable`:

```python
ComposableNode(package='camera_ros', plugin='camera::CameraNode', ...)
```

O transformer trata ambos como `node_raw`, mas usa `plugin` como `executable`:

```python
if short == "ComposableNode":
    return {
        "type": "node_raw",
        "package": kwargs.get("package"),
        "executable": kwargs.get("plugin"),  # ← plugin vai para executable
        "is_composable": True,
        ...
    }
```

No JSON Layer 2, um `ComposableNode` é indistinguível de um `Node` excepto pelo valor do `executable` (que tem `::` no nome, ex: `camera::CameraNode`).

### `ComposableNodeContainer`

```python
ComposableNodeContainer(
    name='camera_container',
    package='rclcpp_components',
    executable='component_container',
    composable_node_descriptions=composable_nodes,
)
```

Estratégia:
1. O container em si é guardado como `NodeAction`
2. Os `ComposableNode` dentro são processados separadamente e guardados como `NodeAction` individuais

```python
if short == "ComposableNodeContainer":
    # Guardar referência para resolver depois (timing correcto)
    nodes_raw = kwargs.get("composable_node_descriptions", [])
    return {
        "type": "composable_container",
        "package": pkg, "executable": exe, "name": name,
        "composable_nodes_ref": nodes_raw,  # ← resolver em _consume_actions
    }
```

Em `_consume_actions`:

```python
elif t == "composable_container":
    # 1. Container como NodeAction
    if pkg and exe:
        self._ld.add_action(self._make_node_action(container_node))

    # 2. Resolver composable_nodes (pode ser var ref ainda não populada)
    nodes_ref = action.get("composable_nodes_ref", [])
    composable_nodes = self._resolve(nodes_ref)
    if isinstance(composable_nodes, dict) and composable_nodes.get("type") == "var":
        composable_nodes = self.variables.get(composable_nodes["name"], [])

    # 3. Processar cada ComposableNode
    self._consume_actions(composable_nodes)
```

**Porquê resolver em `_consume_actions` e não em `_specialize_call`?**

O Lark transforma **bottom-up** — quando `ComposableNodeContainer` é processado, a variável `composable_nodes` pode ainda não estar populada em `self.variables`. O `composable_nodes_ref` guarda a referência e resolve-a mais tarde, quando as variáveis já estão todas definidas.

### `LoadComposableNodes`

```python
LoadComposableNodes(
    target_container=container_name,
    composable_node_descriptions=[
        ComposableNode(package='nav2_controller', plugin='nav2_controller::ControllerServer'),
        ...
    ]
)
```

Os `ComposableNode` são extraídos directamente como `NodeAction`:

```python
if short == "LoadComposableNodes":
    nodes_raw = kwargs.get("composable_node_descriptions", [])
    nodes = [self._resolve(n) for n in nodes_raw]
    return {"type": "load_composable_nodes", "composable_nodes": nodes}
```

Em `_consume_actions`, todos os composable nodes são processados sem criar um container adicional.

---

## 9. Como os OpaqueFunction e For Loops são Tratados

### Problema

```python
def prepare_multiple_nodes(context, ld):
    N = int(N_lc.perform(context))  # runtime!
    for i in range(0, N):           # N desconhecido!
        ld.add_action(Node(package="demo_nodes_cpp", executable="talker", namespace=f"ns{i}"))
```

O `N` depende de runtime. O `for i in range(0, N)` não pode ser expandido estaticamente.

### Estratégia

**Passo 1: Guardar o corpo da função auxiliar**

A gramática foi estendida para que `extra_funcdef` use `func_stmt+` em vez de `extra_item+`:

```lark
extra_funcdef: "def" NAME "(" [extra_args] ")" [ARROW] ":" _NEWLINE _INDENT func_stmt+ _DEDENT
```

O transformer guarda o corpo em `self._aux_functions`:

```python
def extra_funcdef(self, items):
    name = str(items[0])
    body = [item for item in items[1:] if isinstance(item, (tuple, dict, list))]
    self._aux_functions[name] = body
```

**Passo 2: Reconhecer `for` na gramática**

```lark
for_stmt: FOR_HDR suite
FOR_HDR.3: /for[ \t]+[^\n:]+:/
```

O transformer converte em tuplo:

```python
def for_stmt(self, items):
    hdr = str(items[0])  # ex: "for i in range(0, N):"
    suite = items[1]
    m = re.match(r'for\s+(\w+)\s+in\s+(.+):\s*$', hdr)
    var = m.group(1)      # → "i"
    iterator = m.group(2) # → "range(0, N)"
    return ("for_block", var, iterator, suite)
```

**Passo 3: Reconhecer `OpaqueFunction`**

```python
if short == "OpaqueFunction":
    func = kwargs.get("function")
    func_name = func.get("name") if isinstance(func, dict) else str(func)
    return {"type": "opaque_function", "function": func_name, "args": ...}
```

**Passo 4: Processar a função auxiliar**

Em `_consume_actions`, quando encontra `opaque_function`:

```python
elif t == "opaque_function":
    func_name = action.get("function")
    if func_name and func_name in self._aux_functions:
        self._consume_aux_function(func_name)
```

`_consume_aux_function` analisa o corpo da função e quando encontra um `for_block`, chama `_process_for_block`:

```python
def _process_for_block(self, var, iterator, suite):
    # Resolver a variável do range
    m = re.match(r"range\s*\(\s*(?:0\s*,\s*)?(.+?)\s*\)", iterator)
    if m:
        raw_n = m.group(1)  # → "N"
        # Tentar resolver N → LaunchConfiguration('num_node_pairs')
        resolved = self._resolve({"type": "var", "name": raw_n})
        if isinstance(resolved, dict) and resolved.get("type") == "launch_config":
            range_var = resolved.get("name")  # → "num_node_pairs"

    # Condição simbólica
    loop_condition = f"for {var} in range($(arg {range_var}))"
    # → "for i in range($(arg num_node_pairs))"

    # Extrair nodes com a condição
    for stmt in suite:
        if isinstance(stmt, dict) and stmt.get("type") == "add_action":
            action = self._resolve(stmt["action"])
            if isinstance(action, dict) and action.get("type") == "node_raw":
                self._ld.add_action(self._make_node_action(action, loop_condition))
```

**Resultado:**

```
NODE  demo_nodes_cpp / talker   [if: for i in range($(arg num_node_pairs))]
NODE  demo_nodes_cpp / listener [if: for i in range($(arg num_node_pairs))]
```

Os nodes são extraídos com uma condição simbólica que comunica ao HAROS que estes nodes são instanciados `num_node_pairs` vezes, mas que o valor exacto só é conhecido em runtime.

---

## 10. Como os Valores Simbólicos são Representados

### `LaunchSubstitution` — União Discriminada

Todo o valor no Layer 2 é uma `LaunchSubstitution` com um `type` discriminado:

```python
class SubstitutionType(str, Enum):
    LITERAL             = "literal"
    ARGUMENT_REFERENCE  = "argument_reference"
    ENVIRONMENT_VARIABLE = "environment_variable"
    FILE_PATH           = "file_path"
    EXPRESSION          = "expression"
```

### Método `_sub` — Conversor Universal

O método `_sub` nos três transformers converte qualquer valor raw para `LaunchSubstitution`:

```python
def _sub(self, value) -> LaunchSubstitution:
    if isinstance(value, LaunchSubstitution):
        return value  # já é LaunchSubstitution

    if isinstance(value, dict):
        t = value.get("type")
        if t == "launch_config":
            return LaunchSubstitution.argument_reference(value["name"], value.get("default"))
        if t == "env_var":
            return LaunchSubstitution.environment_variable(value["name"])

    s = str(value)
    # XML: $(var name) ou $(arg name)
    m = re.match(r'^\$\((var|arg)\s+(\S+)\)$', s)
    if m: return LaunchSubstitution.argument_reference(m.group(2))

    # XML: $(env NAME)
    m = re.match(r'^\$\(env\s+(\S+)\)$', s)
    if m: return LaunchSubstitution.environment_variable(m.group(1))

    # XML: $(find-pkg-share pkg)/path
    m = re.match(r'^\$\(find-pkg-share\s+(\S+)\)/(.+)$', s)
    if m: return LaunchSubstitution.file_path(m.group(1), m.group(2))

    return LaunchSubstitution.literal(s)  # fallback — valor literal
```

### Display simbólico

O método `display()` converte para notação legível:

```python
def display(self) -> str:
    if self.type == LITERAL:             return str(self.value)
    if self.type == ARGUMENT_REFERENCE:  return f"$(arg {self.argument_name})"
    if self.type == ENVIRONMENT_VARIABLE: return f"$(env {self.variable_name})"
    if self.type == FILE_PATH:           return f"$(find-pkg-share {self.package})/{self.relative_path}"
    if self.type == EXPRESSION:          return f"$(expr {self.expression})"
```

---

## 11. Como a Proveniência é Guardada

### `SourceRef` (conforme `common.pdf`)

```json
{
  "file_path": "examples/real-python/spawn_robot.launch.py",
  "line_start": null,
  "line_end": null,
  "column_start": null,
  "column_end": null,
  "note": null
}
```

Actualmente só `file_path` é populado — os números de linha não são extraídos pelo parser Lark sem instrumentação adicional.

### `ElementProvenance` (conforme `common.pdf`)

```json
{
  "extraction_method": "static_analysis",
  "confidence": 1.0,
  "source_location": {"file_path": "..."},
  "extractor_version": "ProjetoEL-2025",
  "extraction_context": {"parser": "lark", "format": "py"},
  "additional_locations": [],
  "extraction_timestamp": null,
  "notes": null
}
```

### Escala de `confidence`

| Valor | Situação |
|-------|----------|
| `1.0` | Node literal sem condições |
| `0.95` | `LaunchDescription` XML/YAML |
| `0.9` | Node dentro de `if` |
| `0.85` | `LaunchDescription` Python |
| `0.8` | Arg extraído como "órfão" (não adicionado explicitamente ao `ld`) |

---

## 12. Como os IDs são Gerados

### Formato

```
la:<file_id>:<hash8>#<ordinal>
```

### Geração

```python
class ActionIDGenerator:
    def generate(self, source_snippet: str = "") -> str:
        normalized = _normalize_source(source_snippet)
        h = _compute_hash(normalized)    # MD5 truncado a 8 hex chars
        ordinal = self._hash_counts.get(h, 0)
        self._hash_counts[h] = ordinal + 1
        return f"la:{self.file_id}:{h}#{ordinal}"

def _normalize_source(snippet):
    snippet = re.sub(r'#[^\n]*', '', snippet)  # remove comentários
    snippet = snippet.replace("'", '"')          # normaliza aspas
    snippet = re.sub(r'\s+', '', snippet)        # remove espaços
    return snippet
```

### Propriedade de estabilidade entre formatos

O snippet usado para hash é construído a partir dos campos semânticos do node, não do texto fonte:

```python
snippet = f"Node(pkg={pkg},exec={exe},name={name})"
```

Isto garante que o mesmo node em XML e YAML produz o mesmo hash — demonstrado com o `talker_node` que tem hash `190a4ef8` em ambos os formatos.

---

## 13. Casos Especiais e Limitações

### Variáveis não resolvidas (var refs pendentes)

O Lark transforma **bottom-up** — quando `LaunchDescription(declared_args)` é processado, `declared_args` pode ainda estar vazio. A solução é guardar uma referência pendente e resolver mais tarde:

```python
# launch_description() guarda a var ref
def launch_description(self, items):
    source = self._resolve(items[0])
    if isinstance(source, dict) and source.get("type") == "var":
        actions.append(source)  # ← guardada como pendente

# _consume_return resolve depois
def _consume_return(self, value):
    resolved = self._resolve(value)
    for a in resolved["actions"]:
        if isinstance(a, dict) and a.get("type") == "var":
            var_val = self.variables.get(a["name"], [])
            expanded.extend(var_val)  # ← resolvida agora
```

### `OpaqueFunction` com lógica inacessível

Quando a função auxiliar usa callbacks ou lógica impossível de analisar estaticamente, o sistema extrai o máximo possível e ignora o resto:

```python
# Isto não é extraível:
def prepare_nodes(context, *args, **kwargs):
    N = int(N_lc.perform(context))  # runtime
    for i in range(0, N):           # N desconhecido → extraído simbolicamente
        nodes.append(Node(...))      # ← extraído como node condicional
```

### `has_resource()` e condições de runtime

```python
if has_resource('packages', 'image_view'):
    composable_nodes.append(ComposableNode(...))
```

O node é extraído com condição `["truthy", ["var_get", "has_resource('packages', 'image_view')"]]`. Não é o formato IR ideal mas comunica que é uma condição de runtime não avaliável estaticamente.

### Paths dinâmicos em includes

```python
IncludeLaunchDescription(
    PythonLaunchDescriptionSource(
        os.path.join(pkg_var, 'launch', 'world.launch.py')
    )
)
```

O `pkg_var` não é resolvível estaticamente. O transformer tenta extrair o nome do ficheiro do final do caminho. Quando falha, o `included_launch_id` fica com uma representação do caminho não resolvido — o HAROS consegue identificar que é um include mas não sabe exactamente para que ficheiro.

### f-strings com variáveis de loop

```python
namespace=f"ns{i}"
```

O `i` é a variável do loop. O transformer guarda `"ns{i}"` literalmente — não avalia a f-string porque `i` só é conhecida em runtime.

---

## 14. Caso de Estudo: `navigation_launch.py` — O Caso Mais Complexo

O `navigation_launch.py` é o caso mais difícil dos exemplos do repositório. Tem **3 níveis de profundidade hierárquica**, dois `GroupAction` com tipos mistos de acções dentro, e dois padrões de deployment em paralelo (standalone vs composable).

### Estrutura do ficheiro

```python
# Grupo 1: nodes standalone (activo quando use_composition=False)
load_nodes = GroupAction(
    condition=IfCondition(PythonExpression(['not ', use_composition])),
    actions=[
        SetParameter('use_sim_time', use_sim_time),        # ← SetParameter
        PushROSNamespace(namespace=namespace),              # ← PushNamespace
        Node(package='nav2_controller', ...),              # ← 12 Nodes
        Node(package='nav2_smoother', ...),
        # ... 10 nodes mais
    ]
)

# Grupo 2: composable nodes (activo quando use_composition=True)
load_composable_nodes = GroupAction(
    condition=IfCondition(use_composition),
    actions=[
        SetParameter('use_sim_time', use_sim_time),        # ← SetParameter
        PushROSNamespace(namespace=namespace),              # ← PushNamespace
        LoadComposableNodes(                               # ← 3.º nível
            target_container=container_name_full,
            composable_node_descriptions=[
                ComposableNode(package='nav2_controller', plugin='nav2_controller::ControllerServer'),
                ComposableNode(package='nav2_smoother',   plugin='nav2_smoother::SmootherServer'),
                # ... 10 ComposableNodes mais
            ]
        )
    ]
)
```

### Hierarquia resultante

```
launch_sequence: [set_env, group_load_nodes, group_load_composable]
  │
  ├── group_load_nodes  (13 filhos)
  │     ├── set_parameter (use_sim_time)
  │     ├── push_namespace
  │     ├── node: controller_server
  │     ├── node: smoother_server
  │     ├── node: planner_server
  │     ├── ... (9 nodes mais)
  │     └── node: lifecycle_manager_navigation
  │
  └── group_load_composable  (13 filhos)
        ├── set_parameter (use_sim_time)
        ├── push_namespace
        └── load_composable_nodes → [12 ComposableNode como NodeAction]
              ├── node: nav2_controller::ControllerServer
              ├── node: nav2_smoother::SmootherServer
              ├── ... (10 mais)
              └── node: nav2_lifecycle_manager::LifecycleManager
```

### Passo a passo da resolução

**Passo 1 — Lark transforma bottom-up**

O Lark começa pelos nós folha. Os `Node(...)` e `ComposableNode(...)` são transformados primeiro pelo `_specialize_call` em dicts `node_raw`. Depois o `LoadComposableNodes(...)` é transformado em `load_composable_nodes` com a lista de composable nodes já resolvida. Depois o `GroupAction(actions=[...])` recebe a lista já processada.

**Passo 2 — `GroupAction` reconhecido em `_specialize_call`**

```python
if short == "GroupAction":
    children = self._resolve(args[0]) if args else self._resolve(kwargs.get("actions", []))
    if not isinstance(children, list):
        children = [children] if children else []
    return {"type": "group_action", "children": children}
```

A lista `actions=` contém já os dicts processados:
- `{"type": "set_parameter", ...}`
- `{"type": "push_namespace", ...}`  
- `{"type": "node_raw", package="nav2_controller", ...}` × 12
- (ou `{"type": "load_composable_nodes", ...}` no segundo grupo)

**Passo 3 — Condição do `GroupAction`**

O `condition=IfCondition(use_composition)` é processado pelo `_condition_expr_to_ir` e guardado no `group_action`:

```python
# Grupo 1:
condition = ["not", ["eq", ["launch_arg_get", "use_composition"], "true"]]

# Grupo 2:
condition = ["eq", ["launch_arg_get", "use_composition"], "true"]
```

**Passo 4 — `_consume_actions` cria o `GroupAction` Layer 2**

Quando encontra `group_action` na lista de acções:

```python
elif t == "group_action":
    group = GroupAction(
        id=self._id_gen.generate("group_action"),
        action_type=ActionType.GROUP,
        provenance=self._provenance(0.9),
    )
    self._ld.add_action(group)   # ← grupo vai para a sequência

    prev_seq = list(self._ld.launch_sequence)
    self._consume_actions(children_items)  # ← processa os filhos
    new_ids = [aid for aid in self._ld.launch_sequence if aid not in prev_seq]

    # Remover filhos da sequência principal
    for aid in new_ids:
        self._ld.launch_sequence.remove(aid)

    group.children = new_ids  # ← filhos atribuídos ao grupo
```

**Passo 5 — Processamento dos filhos do Grupo 1**

Para cada filho na lista `children_items`:

- `set_parameter` → cria `SetParameterAction` e adiciona ao `_ld`
- `push_namespace` → cria `PushNamespaceAction` e adiciona ao `_ld`
- `node_raw` × 12 → `_make_node_action()` para cada um → 12 `NodeAction`

Todos ficam no `_ld.actions` map mas são removidos da `launch_sequence` e atribuídos ao `group.children`.

**Passo 6 — Processamento do `LoadComposableNodes` (Grupo 2)**

O `LoadComposableNodes` dentro do segundo `GroupAction` é processado em `_consume_actions`:

```python
elif t == "load_composable_nodes":
    composable_nodes = action.get("composable_nodes", [])
    if isinstance(composable_nodes, list):
        self._consume_actions(composable_nodes)  # ← processa os 12 ComposableNodes
```

Cada `ComposableNode` é tratado como `node_raw` com `plugin` no campo `executable`:

```python
# ComposableNode(package='nav2_controller', plugin='nav2_controller::ControllerServer')
# →
NodeAction(
    package=LaunchSubstitution.literal("nav2_controller"),
    executable=LaunchSubstitution.literal("nav2_controller::ControllerServer"),
    ...
)
```

Os 12 `NodeAction` resultantes são adicionados ao `_ld.actions` e depois atribuídos como `children` do segundo `GroupAction`.

**Passo 7 — `LaunchConfigAsBool` não reconhecido**

```python
SetParameter('use_sim_time', LaunchConfigAsBool('use_sim_time'))
```

O `LaunchConfigAsBool` é uma classe do `nav2_common` que o transformer não reconhece. Cai no fallback do `_symbolic` e é guardado como string:

```json
"value": {"type": "literal", "value": "LaunchConfigAsBool('use_sim_time')"}
```

No output do terminal aparece como:
```
SET   use_sim_time = LaunchConfigAsBool('use_sim_time')
```

É uma limitação — semanticamente devia ser `argument_reference` mas a classe é externa ao ROS2 base.

### Resultado final — 41 acções

| Localização | Tipo | Count |
|---|---|---|
| `launch_sequence` | `SetParameterAction` | 1 |
| `launch_sequence` | `GroupAction` (load_nodes) | 1 |
| `launch_sequence` | `GroupAction` (load_composable) | 1 |
| `group_load_nodes.children` | `SetParameterAction` | 1 |
| `group_load_nodes.children` | `PushNamespaceAction` | 1 |
| `group_load_nodes.children` | `NodeAction` (standalone) | 12 |
| `group_load_composable.children` | `SetParameterAction` | 1 |
| `group_load_composable.children` | `PushNamespaceAction` | 1 |
| `group_load_composable.children` | `NodeAction` (composable) | 12 |
| **Total** | | **41** |

A `launch_sequence` tem apenas **3 acções** (SET + 2 GROUP). As outras 38 estão no `actions` map como filhos dos grupos — a hierarquia está completamente preservada.

### Verificação

```bash
python3 main.py python examples/real-python/navigation_launch.py
```

Output esperado:
```
39-41 acções  ·  seq=3
GROUP  ns=—  (13 filhos)   [if: not use_composition]
GROUP  ns=—  (13 filhos)   [if: use_composition]
ACÇÕES FILHAS (26): 12 nodes standalone + 12 composable nodes
```


---

## 15. Issue Detection — Layer 6

O `IssueDetector` analisa o `LaunchDescription` Layer 2 e produz `Issue` conforme a especificação `layer6.pdf`. É executado automaticamente após a validação Layer 2.

### Estrutura de um `Issue`

```json
{
  "id": "issue_file_spawn_001",
  "severity": "warning",
  "category": "architecture",
  "description": "Include com path dinâmico não resolvível estaticamente.",
  "affected_entities": [
    {"type": "include", "id": "la:file_spawn:8e31550a#0"}
  ],
  "analysis_tool": "ProjetoEL-extractor",
  "analysis_timestamp": "2025-05-12T10:30:00Z",
  "location": {"file_path": "examples/real-python/spawn_robot.launch.py"},
  "metadata": {
    "included_launch_id": "launch_desc_file_os_path_join_..."
  }
}
```

### Issues detectáveis no Layer 2

#### `node_no_name` — `[INFO]`

```python
Node(package='ros_gz_sim', executable='create')  # sem name=
```

Detectado quando `action.name is None`. O node vai usar o `executable` como nome por omissão em runtime — pode causar conflitos se houver dois nodes com o mesmo executable.

#### `node_runtime_condition` — `[INFO]`

```python
if has_resource('packages', 'image_view'):
    composable_nodes.append(ComposableNode(...))
```

Detectado quando a condição contém `has_resource`. O node só é instanciado se o package existir no sistema — informação de runtime.

#### `opaque_symbolic_node` — `[WARNING]`

```python
for i in range(0, N):
    ld.add_action(Node(package="demo_nodes_cpp", executable="talker"))
```

Detectado quando a condição contém `for` e `range`. O número exacto de instâncias depende do valor de `N` em runtime.

#### `include_unresolved` — `[WARNING]`

```python
IncludeLaunchDescription(
    PythonLaunchDescriptionSource(
        os.path.join(pkg_var, 'launch', 'world.launch.py')
    )
)
```

Detectado quando o `included_launch_id` contém `os_path_join` ou `type____var` — o path não foi resolvível estaticamente.

#### `arg_no_default` — `[WARNING]`

```python
DeclareLaunchArgument('num_pairs')  # sem default_value=
```

Detectado quando `action.default_value is None`. O arg tem de ser sempre fornecido ao invocar o launch file.

#### `arg_orphan` — `[INFO]`

```python
declared_args = []
declared_args.append(DeclareLaunchArgument("num_node_pairs", default_value="1"))
ld = LaunchDescription()  # declared_args nunca adicionado!
```

Detectado quando `action.provenance.confidence < 0.9` — o arg foi extraído por `_extract_orphan_args` porque nunca foi adicionado explicitamente ao `LaunchDescription`.

#### `namespace_implicit` — `[INFO]`

Detectado quando existe um `PushNamespaceAction` no `LaunchDescription` e um `NodeAction` não tem `namespace` explícito — o node vai herdar o namespace do contexto em runtime.

#### `include_self` — `[ERROR]`

Detectado quando `action.included_launch_id == ld.id` — o launch file inclui-se a si próprio, criando um ciclo infinito.

### Limitações — o que não é detectável no Layer 2

Os issues mais graves do `layer6.pdf` requerem informação de camadas superiores:

| Issue | Requer | Camada |
|---|---|---|
| QoS incompatibility | Tópicos publicados/subscritos e seus perfis QoS | Layer 1 + Layer 4 |
| Type mismatch | Tipos de mensagens de cada tópico | Layer 1 |
| Orphan publisher | Grafo completo de comunicação | Layer 4 |
| Rate mismatch | Taxas de publicação | Layer 1/4 |

Estes issues só podem ser detectados pelo HAROS após resolver o Layer 2 em instâncias concretas (Layer 3/4) e cruzar com a informação dos nodes (Layer 1).