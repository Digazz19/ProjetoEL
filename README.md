# ProjetoEL — Extracção e Análise de Arquitecturas ROS2

Projeto da UC **Projeto de Engenharia de Linguagens** (Perfil EL, 2025/26) — Universidade do Minho.

Extracção estática de arquitecturas ROS2 a partir de launch files em **XML**, **YAML** e **Python**, produzindo uma representação intermédia **Layer 2** conforme a especificação do **HAROS**. Para além da extracção, o projecto inclui validação estrutural, geração de issues Layer 6, exportação para RDF/Turtle, validação SHACL, análise ontológica através de queries SPARQL, integração opcional com GraphDB e uma camada de comunicação runtime construída a partir da informação dos nós individuais, dos nós lançados pelo launch file e dos remappings declarados.

---

## 2. Objetivo

Desenvolver uma pipeline de engenharia de linguagens que, dado um ou vários launch files ROS2, consiga:

1. extrair uma representação intermédia normalizada **Layer 2**;
2. preservar a estrutura simbólica dos launch files, incluindo argumentos, nodes, includes, grupos, namespaces, parâmetros, remappings e condições;
3. validar estruturalmente essa representação;
4. gerar issues arquitecturais em formato inspirado no **HAROS Layer 6**;
5. exportar o modelo para **RDF/Turtle**;
6. validar o grafo com **SHACL**;
7. executar queries **SPARQL** para detectar issues directamente sobre a ontologia;
8. construir uma arquitectura runtime de comunicação a partir dos nodes lançados, das interfaces conhecidas dos nodes e dos remappings do launch file;
9. representar topics, publishers, subscribers e perfis QoS;
10. detectar issues de comunicação, como publishers sem subscribers, subscribers sem publishers, nodes isolados, múltiplos publishers no mesmo topic e incompatibilidades de QoS;
11. executar a mesma análise ontológica localmente com `rdflib` ou num triplestore externo como GraphDB.

O output pode ser usado como base para integração com o HAROS ou com ferramentas RDF externas, como GraphDB.

---

## 3. Estrutura do Projeto

```text
ProjetoEL/
├── main.py                              # Ponto de entrada principal
├── test_layer2.py                       # Testes dos exemplos XML/YAML/Python mínimos e HAROS coverage
├── test_launchfiles.py                  # Teste em lote nos 12 launch files Python reais
│
├── models/
│   ├── layer2.py                        # Modelo Layer 2 HAROS
│   ├── layer6.py                        # Issue e ElementRef, inspirados no HAROS Layer 6
│   └── runtime_architecture.py          # Modelo de arquitectura runtime de comunicação
│
├── validation/
│   └── layer2_validator.py              # Validador estrutural Layer 2
│
├── issues/
│   ├── catalog.yaml                     # Catálogo externo de issues
│   ├── catalog.py                       # Loader do catálogo
│   ├── detector.py                      # Issues estruturais sobre LaunchDescription
│   ├── ontology_detector.py             # Issues ontológicos via SPARQL local
│   ├── graphdb_detector.py              # Issues ontológicos via GraphDB
│   └── io.py                            # Escrita de issues em JSON
│
├── ontology/
│   ├── ros_launch.ttl                   # Ontologia base Layer 2 + comunicação runtime
│   ├── shapes.ttl                       # Shapes SHACL
│   └── queries/
│       ├── node_no_name.rq
│       ├── include_unresolved.rq
│       ├── arg_no_default.rq
│       ├── action_without_provenance.rq
│       └── communication/               # Queries de comunicação runtime
│           ├── isolated_node.rq
│           ├── publisher_without_subscriber.rq
│           ├── subscriber_without_publisher.rq
│           ├── topic_multiple_publishers.rq
│           └── qos_reliability_mismatch.rq
│
├── scripts/
│   ├── ontology/
│   │   ├── export_layer2_to_rdf.py
│   │   ├── export_all_layer2_to_rdf.py
│   │   ├── run_ontology_issues.py
│   │   ├── run_all_ontology_pipeline.py
│   │   ├── validate_rdf.py
│   │   └── validate_all_rdf.py
│   │
│   ├── communication/
│   │   ├── build_runtime_architecture.py
│   │   ├── export_architecture_to_rdf.py
│   │   ├── run_communication_issues.py
│   │   └── run_communication_pipeline.py
│   │
│   ├── graphdb/
│   │   ├── graphdb_clear.py
│   │   ├── graphdb_upload.py
│   │   ├── graphdb_query.py
│   │   └── run_graphdb_issues.py
│   │
│   └── demos/
│       ├── demo.sh
│       ├── demo_graphdb.sh
│       └── demo_communication.sh
│
├── node_interfaces/                     # Interfaces conhecidas dos nodes individuais
│   ├── robot.communication.yaml
│   └── communication_demo.communication.yaml
│
├── parsers/
│   ├── xml/
│   ├── yaml/
│   └── python/
│
├── examples/
│   ├── layer2-minimal/                  # 30 exemplos mínimos
│   ├── layer2-haros-coverage/           # 28 exemplos de cobertura Layer 2
│   ├── real-python/                     # 12 launch files ROS2 reais
│   └── communication/                   # Exemplo controlado para comunicação
│
└── output/                              # Artefactos gerados
    ├── *.layer2.json
    ├── layer2-tests/*.layer2.json
    ├── architecture/*.architecture.json
    ├── rdf/*.ttl
    ├── rdf/architecture/*.architecture.ttl
    └── issues/*.json
```

---

## 📋 Índice Geral

1. [ProjetoEL — Extracção e Análise de Arquitecturas ROS2](#projetoel--extracção-e-análise-de-arquitecturas-ros2)
2. [Objetivo](#2-objetivo)
3. [Estrutura do Projeto](#3-estrutura-do-projeto)
4. [Visão Geral da Pipeline](#4-visão-geral-da-pipeline)
5. [Utilização](#5-utilização)
6. [Outputs](#6-outputs)
7. [Modelo Layer 2](#7-modelo-layer-2)
8. [Estratégia detalhada de extracção Layer 2](#8-estratégia-detalhada-de-extracção-layer-2)
   1. [Argumentos](#81-argumentos)
   2. [Nodes](#82-nodes)
   3. [Includes](#83-includes)
   4. [Grupos](#84-grupos)
   5. [Namespaces](#85-namespaces)
   6. [Condições](#86-condições)
   7. [ComposableNodes](#87-composablenodes)
   8. [OpaqueFunction e loops](#88-opaquefunction-e-loops)
   9. [Valores simbólicos](#89-valores-simbólicos)
   10. [Proveniência](#810-proveniência)
   11. [IDs](#811-ids)
9. [Matriz de Suporte Layer 2](#9-matriz-de-suporte-layer-2)
10. [Validação Layer 2](#10-validação-layer-2)
11. [Exportação RDF/Turtle e validação SHACL](#11-exportação-rdfturtle-e-validação-shacl)
12. [Issue Detection — Layer 6](#12-issue-detection--layer-6)
13. [Arquitetura Runtime e Grafo de Comunicação](#13-arquitetura-runtime-e-grafo-de-comunicação)
14. [Backend GraphDB](#14-backend-graphdb)
15. [Pipeline Operacional e Demo](#15-pipeline-operacional-e-demo)
16. [Resultados de Teste](#16-resultados-de-teste)
17. [Limitações Conhecidas](#17-limitações-conhecidas)
18. [Referências](#18-referências)
19. [Autores](#19-autores)

---

## 4. Visão Geral da Pipeline

Cada launch file passa pelas etapas originais de parsing e transformação. Na versão actual, essa pipeline foi estendida com validação, geração de issues, exportação RDF e análise ontológica:

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
        ├──► print_summary()              → Output legível no terminal
        ├──► to_json()                    → JSON Layer 2 guardado em output/
        ├──► Layer2Validator              → validação estrutural Layer 2
        ├──► IssueDetector                → issues estruturais Layer 6
        │                                      output/issues/*.issues.json
        └──► export_layer2_to_rdf.py      → RDF/Turtle em output/rdf/
                                                │
                                                ▼
                                           SHACL / SPARQL
                                                │
                                                └──► issues ontológicos Layer 6
                                                     output/issues/*.ontology.issues.json
```

O transformer percorre a árvore **bottom-up** — os nós folha são processados primeiro, e os resultados sobem até ao topo. Isto significa que quando o transformer processa um `Node(...)`, já tem os valores dos seus argumentos resolvidos.

A parte de análise foi separada do modelo: `models/layer2.py` mantém a representação Layer 2; `validation/layer2_validator.py` contém a validação estrutural; `models/layer6.py` contém a estrutura dos resultados de análise; e a pasta `issues/` contém os detectores, o catálogo externo de issues e a escrita dos resultados.

Numa fase posterior, a pipeline foi também estendida com uma camada de arquitectura runtime anotada. Esta camada não tenta inferir automaticamente publishers, subscribers e QoS a partir do código dos nodes, porque essa informação normalmente não está disponível nos launch files. Em vez disso, parte do Layer 2 e de ficheiros auxiliares de comunicação escritos em YAML. A partir dessas anotações, o sistema constrói uma arquitectura resolvida com `RuntimeNode`, `Topic`, `Publication`, `Subscription` e `QoSProfile`, exporta essa arquitectura para RDF/Turtle e executa queries SPARQL de comunicação.

Esta extensão permite detectar problemas que não são observáveis directamente no Layer 2, como publishers sem subscribers, subscribers sem publishers, tópicos com múltiplos publishers, nodes isolados e incompatibilidades simples de QoS.

---

## 5. Utilização

### Processar um ficheiro único

```bash
python3 main.py python examples/real-python/spawn_robot.launch.py
python3 main.py xml    examples/example.launch.xml
python3 main.py yaml   examples/example.launch.yaml
python3 main.py auto   examples/example.launch.xml
```

### Processar uma pasta inteira

```bash
python3 main.py python examples/real-python
```

### Opções

- `--tree` — imprime a árvore de parsing;
- `--json` — também imprime o JSON no terminal;
- `--json-file` — força guardar JSON, embora o JSON já seja guardado por omissão.

### Testes

```bash
python3 test_layer2.py examples/layer2-minimal
python3 test_layer2.py examples/layer2-haros-coverage
python3 test_launchfiles.py examples/real-python
```

### Demo completa

```bash
./scripts/demos/demo.sh
```

A demo executa compilação, testes, extracção Layer 2, geração de issues estruturais, exportação RDF/Turtle, geração de issues ontológicos por SPARQL, validação SHACL, geração de arquitectura runtime de comunicação e issues de comunicação.

#### Pipeline ontológica Layer 2

```bash
python3 scripts/ontology/run_all_ontology_pipeline.py output
```

#### Pipeline de comunicação

```bash
python3 scripts/communication/run_communication_pipeline.py \
  output/robot.launch.layer2.json \
  node_interfaces/robot.communication.yaml
```

### GraphDB

O GraphDB é opcional e exige um serviço GraphDB a correr localmente.

```bash
python3 scripts/graphdb/graphdb_clear.py --repo haros
python3 scripts/graphdb/graphdb_upload.py output/rdf --repo haros
python3 scripts/graphdb/run_graphdb_issues.py --repo haros
```

### Dependências

- Python 3.12+
- Lark
- PyYAML
- rdflib
- pyshacl
- requests

Instalação:

```bash
pip install -r requirements.txt
```

---

## 6. Outputs

O projecto gera vários artefactos:

| Artefacto | Caminho | Descrição |
|---|---|---|
| Layer 2 JSON | `output/*.layer2.json` | Modelo simbólico dos launch files reais |
| Layer 2 JSON de testes | `output/layer2-tests/*.layer2.json` | Modelos dos exemplos mínimos e de cobertura |
| Issues estruturais | `output/issues/*.issues.json` | Issues gerados sobre o `LaunchDescription` em memória |
| RDF/Turtle Layer 2 | `output/rdf/*.layer2.ttl` | Exportação ontológica do modelo Layer 2 |
| Issues ontológicos | `output/issues/*.ontology.issues.json` | Issues gerados por queries SPARQL sobre RDF Layer 2 |
| RuntimeArchitecture JSON | `output/architecture/*.architecture.json` | Arquitectura runtime de comunicação |
| RuntimeArchitecture RDF | `output/rdf/architecture/*.architecture.ttl` | Exportação RDF da arquitectura de comunicação |
| Issues de comunicação | `output/issues/*.communication.issues.json` | Issues de comunicação detectados sobre a arquitectura runtime |
| Issues GraphDB | `output/issues/graphdb.issues.json` | Issues gerados a partir de queries SPARQL executadas no GraphDB |

---

## 7. Modelo Layer 2

Conforme a especificação `haros_layer2.pdf`, o modelo captura um **programa simbólico de launch**. A camada Layer 2 representa possibilidades de instanciação, não necessariamente nodes runtime concretos.

### Estrutura principal

```python
LaunchDescription:
    id: string                        # "launch_desc_<file_id>"
    launch_file_id: string            # ID do ficheiro Layer 0
    format: "xml" | "yaml" | "python"
    actions: Dict[str, LaunchAction]  # Mapa de acções por ID
    launch_sequence: List[str]        # Ordem de execução dos IDs de topo
    provenance: ElementProvenance
```

### Tipos de Acções

| Acção | Descrição |
|---|---|
| `DeclareArgumentAction` | Declaração de argumento launch |
| `SetParameterAction` | Definição de parâmetro no escopo |
| `PushNamespaceAction` | Introdução de namespace |
| `NodeAction` | Instanciação simbólica de node |
| `IncludeAction` | Inclusão de outro launch file |
| `GroupAction` | Agrupamento com scope opcional |

### IDs Hash-based Determinísticos

Formato: `la:<file_id>:<hash8>#<ordinal>`

- `la:` — prefixo de launch action
- `<file_id>` — ID do ficheiro de origem
- `<hash8>` — hash de 8 caracteres sobre o snippet normalizado
- `<ordinal>` — contador para colisões

**Propriedades:**

- estáveis a formatting, comentários e ordem de kwargs;
- determinísticos, isto é, a mesma fonte gera o mesmo ID;
- adequados a patching e referência estável em análises posteriores.

### LaunchSubstitution

Valores simbólicos que permanecem não avaliados até haver configuração concreta ou análise posterior:

```json
{"type": "literal", "value": 30}
{"type": "argument_reference", "argument_name": "use_sim"}
{"type": "environment_variable", "variable_name": "ROS_DISTRO"}
{"type": "file_path", "package": "pkg", "relative_path": "config.yaml"}
{"type": "expression", "expression": [...]}
```

### Condições IR

As condições são guardadas como árvores simbólicas:

```python
# IfCondition(LaunchConfiguration('use_sim'))
["eq", ["launch_arg_get", "use_sim"], "true"]

# UnlessCondition(LaunchConfiguration('use_sim'))
["not", ["eq", ["launch_arg_get", "use_sim"], "true"]]
```

Operadores suportados incluem `or`, `and`, `not`, `eq`, `neq`, `lt`, `gt`, `lte`, `gte`, `truthy`.

### Proveniência

Cada acção e o próprio `LaunchDescription` carregam proveniência:

```json
{
  "extraction_method": "static_analysis",
  "source_location": {"file_path": "path/to/file.launch.py"},
  "confidence": 1.0
}
```

A confidence reflecte o nível de certeza da extracção: valores altos para padrões estáticos directos, valores mais baixos para construções condicionais, dinâmicas ou inferidas.

---

## 8. Estratégia detalhada de extracção Layer 2

Esta secção detalha a estratégia usada para extrair e guardar cada tipo de informação presente nos launch files ROS2 em XML, YAML e Python, produzindo a representação intermédia **Layer 2** conforme a especificação HAROS.

A estratégia aparece aqui antes da validação, da geração de issues e da exportação RDF porque essa é a ordem lógica da pipeline: primeiro extrai-se o modelo Layer 2; depois esse modelo é validado, analisado e exportado.

---

### 8.1 Argumentos

#### Formato Layer 2

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

#### Em Python

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

#### Caso especial: args declarados mas não adicionados ao LaunchDescription

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

#### Em XML

O parser reconhece `<arg name="x" default="y"/>` e o transformer converte directamente:

```python
def arg(self, items):
    attrs = dict(items)
    return {"type": "arg", "name": attrs.get("name"), "default": attrs.get("default"), ...}
```

#### Padrão `list.append()`

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

### 8.2 Nodes

#### Formato Layer 2

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

#### Em Python — `_make_node_action`

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

#### `IfCondition` e `UnlessCondition`

O transformer reconhece `condition=IfCondition(LaunchConfiguration('x'))` no `_specialize_call` via `_condition_expr_to_ir`:

```python
if short == "IfCondition":
    return {"condition": ["eq", ["launch_arg_get", arg_name], "true"]}

if short == "UnlessCondition":
    return {"condition": ["not", ["eq", ["launch_arg_get", arg_name], "true"]]}
```

O kwarg `condition` do `Node` é guardado no `node_raw` e depois aplicado em `_make_node_action`.

#### Em XML

```xml
<node pkg="nav2" exec="controller" if="$(var use_sim)"/>
```

O atributo `if` é convertido para IR:

```python
if item.get("if"):
    cond_list.append(_parse_launch_condition_to_ir(item["if"]))
```

---

### 8.3 Includes

#### Formato Layer 2

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

#### Estratégia de resolução do caminho

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

#### Display legível no terminal

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

### 8.4 Grupos

#### Formato Layer 2

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

#### Em XML

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

#### Em Python — `GroupAction([...])`

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

### 8.5 Namespaces

#### `PushRosNamespace` em Python

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

#### `<push-ros-namespace>` em XML

```xml
<push-ros-namespace namespace="$(var robot_name)"/>
```

O transformer XML tem um método dedicado:

```python
def push_ros_namespace(self, items):
    attrs = dict(items)
    return {"type": "push_namespace", "namespace": attrs.get("namespace")}
```

#### Namespace em GroupAction

Quando um `GroupAction` tem namespace, este é guardado no campo `namespace` do grupo:

```json
{
  "action_type": "group",
  "namespace": {"type": "literal", "value": "/simulation"},
  "children": [...]
}
```

---

### 8.6 Condições

#### Formato IR (Intermediate Representation)

As condições são guardadas como **árvores S-expression**:

```python
# if os.environ['ROS_DISTRO'] == 'humble':
[["eq", ["env_get", "ROS_DISTRO"], "humble"]]

# if ROS_DISTRO == 'humble':
[["eq", ["var_get", "ROS_DISTRO"], "humble"]]

# IfCondition(LaunchConfiguration('use_sim'))
[["eq", ["launch_arg_get", "use_sim"], "true"]]

# UnlessCondition(LaunchConfiguration('use_sim'))
[["not", ["eq", ["launch_arg_get", "use_sim"], "true"]]]

# if N<1 or N>5:
[["or", ["lt", ["var_get", "N"], "1"], ["gt", ["var_get", "N"], "5"]]]

# for i in range($(arg num_node_pairs)):
[["truthy", ["var_get", "for i in range($(arg num_node_pairs))"]]]
```

#### Condições em Python (`if` statements)

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
    if name.startswith("os.environ"):
        return ["env_get", extracted_name]
    if "LaunchConfiguration" in name:
        return ["launch_arg_get", extracted_name]
    return ["var_get", name]
```

Nota: nomes em maiúsculas já não são automaticamente tratados como variáveis de ambiente. Isto evita classificar variáveis locais como `N`, `NUM_NODES` ou `ROS_DISTRO` como environment variables sem evidência explícita. Para obter `env_get`, a condição tem de usar `os.environ[...]` em Python ou `$(env ...)` em XML/YAML.

#### Condições em XML (`if`/`unless`)

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

Em XML e YAML, as condições são processadas transversalmente por `_conditions_for_item`. Isto significa que `if` e `unless` podem ser associados a várias `LaunchAction`, não apenas a `NodeAction`.

Actions atualmente cobertas:

```text
DeclareArgumentAction
SetParameterAction
IncludeAction
PushNamespaceAction
GroupAction
NodeAction
```

Exemplo:

```xml
<include file="sensors.launch.xml" if="$(var use_sensors)"/>
<group unless="$(var disable_navigation)">
    <node pkg="nav2" exec="controller"/>
</group>
```

No caso dos grupos, a condição fica guardada no próprio GroupAction. Os filhos não recebem uma cópia dessa condição, porque a hierarquia Layer 2 já indica que eles pertencem ao grupo condicionado.

---

#### Combinação de condições exteriores e intrínsecas

Uma action pode ter dois tipos de condição ao mesmo tempo:

1. uma condição exterior, por estar dentro de um `if`, `for`, `OpaqueFunction` ou outro contexto condicionado;
2. uma condição intrínseca, definida diretamente na action, por exemplo `condition=IfCondition(...)`.

Exemplo:

```python
if has_resource('packages', 'image_view'):
    composable_nodes.append(
        ComposableNode(
            package='image_view',
            plugin='image_view::ImageViewNode',
            condition=IfCondition(use_image_view)
        )
    )
```

Neste caso, o node só deve existir se as duas condições forem verdadeiras:

```python
[
  "and",
  ["truthy", ["var_get", "has_resource('packages', 'image_view')"]],
  ["eq", ["launch_arg_get", "use_image_view"], "true"]
]
```

A combinação é feita em *_make_node_action*:

```python
outer_condition = self._condition_to_ir(condition)
intrinsic_condition = self._condition_to_ir(node_data.get("condition"))
combined_condition = self._and_ir(outer_condition, intrinsic_condition)
cond_list = [combined_condition] if combined_condition else []
```

Isto evita perder a condição própria do node quando ele também aparece dentro de um ramo condicionado.

---

### 8.7 ComposableNodes

#### `ComposableNode` — representado como `NodeAction`

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

#### `ComposableNodeContainer`

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

#### `LoadComposableNodes`

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

### 8.8 OpaqueFunction e loops

#### Problema

```python
def prepare_multiple_nodes(context, ld):
    N = int(N_lc.perform(context))  # runtime!
    for i in range(0, N):           # N desconhecido!
        ld.add_action(Node(package="demo_nodes_cpp", executable="talker", namespace=f"ns{i}"))
```

O `N` depende de runtime. O `for i in range(0, N)` não pode ser expandido estaticamente.

#### Estratégia

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

### 8.9 Valores simbólicos

#### `LaunchSubstitution` — União Discriminada

Todo o valor no Layer 2 é uma `LaunchSubstitution` com um `type` discriminado:

```python
class SubstitutionType(str, Enum):
    LITERAL             = "literal"
    ARGUMENT_REFERENCE  = "argument_reference"
    ENVIRONMENT_VARIABLE = "environment_variable"
    FILE_PATH           = "file_path"
    EXPRESSION          = "expression"
```

#### Método `_sub` — Conversor Universal

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

#### Display simbólico

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

### 8.10 Proveniência

#### `SourceRef` (conforme `common.pdf`)

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

#### `ElementProvenance` (conforme `common.pdf`)

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

#### Escala de `confidence`

| Valor | Situação |
|-------|----------|
| `1.0` | Node literal sem condições |
| `0.95` | `LaunchDescription` XML/YAML |
| `0.9` | Action condicionada ou extraída com alguma incerteza simbólica |
| `0.85` | `LaunchDescription` Python |
| `0.8` | Arg extraído como "órfão" (não adicionado explicitamente ao `ld`) |

---

### 8.11 IDs

#### Formato

```
la:<file_id>:<hash8>#<ordinal>
```

#### Geração

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

#### Propriedade de estabilidade entre formatos

O snippet usado para hash é construído a partir dos campos semânticos do node, não do texto fonte:

```python
snippet = f"Node(pkg={pkg},exec={exe},name={name})"
```

Isto garante que o mesmo node em XML e YAML produz o mesmo hash — demonstrado com o `talker_node` que tem hash `190a4ef8` em ambos os formatos.

---

### 8.12 Casos especiais e limitações

#### Variáveis não resolvidas (var refs pendentes)

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

#### `OpaqueFunction` com lógica inacessível

Quando a função auxiliar usa callbacks ou lógica impossível de analisar estaticamente, o sistema extrai o máximo possível e ignora o resto:

```python
# Isto não é extraível:
def prepare_nodes(context, *args, **kwargs):
    N = int(N_lc.perform(context))  # runtime
    for i in range(0, N):           # N desconhecido → extraído simbolicamente
        nodes.append(Node(...))      # ← extraído como node condicional
```

#### `has_resource()` e condições de runtime

```python
if has_resource('packages', 'image_view'):
    composable_nodes.append(ComposableNode(...))
```

O node é extraído com condição `["truthy", ["var_get", "has_resource('packages', 'image_view')"]]`. Não é o formato IR ideal mas comunica que é uma condição de runtime não avaliável estaticamente.

#### Paths dinâmicos em includes

```python
IncludeLaunchDescription(
    PythonLaunchDescriptionSource(
        os.path.join(pkg_var, 'launch', 'world.launch.py')
    )
)
```

O `pkg_var` não é resolvível estaticamente. O transformer tenta extrair o nome do ficheiro do final do caminho. Quando falha, o `included_launch_id` fica com uma representação do caminho não resolvido — o HAROS consegue identificar que é um include mas não sabe exactamente para que ficheiro.

#### f-strings com variáveis de loop

```python
namespace=f"ns{i}"
```

O `i` é a variável do loop. O transformer guarda `"ns{i}"` literalmente — não avalia a f-string porque `i` só é conhecida em runtime.

---

### 8.13 Caso de estudo: `navigation_launch.py`

O `navigation_launch.py` é o caso mais difícil dos exemplos do repositório. Tem **3 níveis de profundidade hierárquica**, dois `GroupAction` com tipos mistos de acções dentro, e dois padrões de deployment em paralelo (standalone vs composable).

#### Estrutura do ficheiro

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

#### Hierarquia resultante

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

#### Passo a passo da resolução

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

O `condition=IfCondition(use_composition)` é preservado no `group_action` e, ao criar o `GroupAction` Layer 2, é convertido para IR e guardado no campo `conditions` do próprio grupo.

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
        conditions=cond_list,
        provenance=self._provenance(0.9 if cond_list else 1.0),
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

#### Resultado final — 41 acções

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

#### Verificação

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

## 9. Matriz de Suporte Layer 2

### Funcionalidades suportadas

### Parsing — XML

- `<node>`, `<arg>`, `<include>`, `<group>`, `<let>`, `<set_env>`;
- `<executable>`, `<param>`, `<remap>`, `<env>`;
- atributos `if` e `unless`;
- substituições `$(var ...)`, `$(env ...)`, `$(find-pkg-share ...)`.

### Parsing — YAML

- estrutura YAML launch ROS2 (`launch:` → elementos);
- `node`, `arg`, `include`, `group`, `let`, `set_env`;
- `executable`, `param`, `remap`, `env`;
- indentação via `YamlIndenter`.

### Parsing — Python

- `Node`, `DeclareLaunchArgument`, `IncludeLaunchDescription`;
- `SetEnvironmentVariable`, `ExecuteProcess`;
- `PushRosNamespace` → `PushNamespaceAction`;
- `GroupAction` com preservação de hierarquia;
- `ComposableNode`, `ComposableNodeContainer`, `LoadComposableNodes`;
- `LaunchConfiguration` → `argument_reference`;
- `os.environ` → `environment_variable`;
- `list.append()` para construção incremental;
- condições `if/elif/else` com IR;
- f-strings, subscripts, tuple unpacking;
- `OpaqueFunction` e loops em padrões suportados;
- variáveis não resolvidas mantidas como referências simbólicas.

---

Esta matriz documenta o subconjunto de ROS 2 launch suportado pelo extrator Layer 2.

---

### Localização dos testes

Testes canónicos mínimos:

`examples/layer2-minimal/`

Testes de cobertura HAROS Layer 2:

`examples/layer2-haros-coverage/`

JSONs Layer 2 gerados:

`output/layer2-tests/`

RDF/Turtle gerado:

`output/rdf/`

Ontologia e regras SHACL:

`ontology/ros_launch.ttl`  
`ontology/shapes.ttl`

Scripts principais:

| Script | Função |
|---|---|
| `test_layer2.py` | Executa os testes canónicos sobre launch files XML, YAML e Python. Para cada ficheiro, chama o parser correspondente, gera JSON Layer 2, verifica a estrutura esperada e executa o `Layer2Validator`. |
| `scripts/ontology/export_layer2_to_rdf.py` | Converte um ficheiro JSON Layer 2 individual para RDF/Turtle, usando o vocabulário definido em `ontology/ros_launch.ttl`. |
| `scripts/ontology/export_all_layer2_to_rdf.py` | Executa a conversão em lote. Percorre todos os ficheiros `.layer2.json` em `output/layer2-tests/` e chama `export_layer2_to_rdf.py` para cada um. |
| `scripts/ontology/validate_rdf.py` | Valida um ficheiro RDF/Turtle individual contra as regras SHACL em `ontology/shapes.ttl`, usando `pyshacl`. |
| `scripts/ontology/validate_all_rdf.py` | Executa a validação em lote. Percorre todos os ficheiros `.ttl` em `output/rdf/` e chama `validate_rdf.py` para cada um. |

---

### Suporte atual — testes mínimos

| Feature | XML | YAML | Python | Testes | Estado |
|---|---:|---:|---:|---|---|
| NodeAction | sim | sim | sim | `node.launch.*` | suportado |
| DeclareArgumentAction | sim | sim | sim | `args.launch.*` | suportado |
| Node parameters | sim | sim | sim | `params.launch.*` | suportado |
| Remappings | sim | sim | sim | `remaps.launch.*` | suportado |
| IncludeAction | sim | sim | sim | `include.launch.*` | suportado |
| GroupAction + PushNamespaceAction | sim | sim | sim | `group_namespace.launch.*` | suportado |
| Conditions simples | sim | sim | sim | `conditions.launch.*` | suportado |
| SetEnvironmentVariable / set_env | sim | sim | sim | `env.launch.*` | parcial |
| Launch argument substitutions | sim | sim | sim | `substitutions_arg.launch.*` | suportado |
| Nested groups | sim | sim | sim | `nested_groups.launch.*` | suportado |

Resultado:

```txt
PASS: 30
FAIL: 0
```

---

### Cobertura HAROS Layer 2 adicional

| Feature                                 | XML | YAML | Python | Testes                              | Estado    |
| --------------------------------------- | --: | ---: | -----: | ----------------------------------- | --------- |
| Conditions com `and`                    | sim |  sim |    sim | `condition_and.launch.*`            | suportado |
| Conditions com `or`                     | sim |  sim |    sim | `condition_or.launch.*`             | suportado |
| Conditions com `not`                    | sim |  sim |    sim | `condition_not.launch.*`            | suportado |
| Group com SetParameterAction            | sim |  sim |    sim | `group_set_params.launch.*`         | suportado |
| IncludeAction com argument_mappings     | sim |  sim |    sim | `include_args.launch.*`             | suportado |
| LaunchSubstitution.file_path            | sim |  sim |    sim | `filepath_substitution.launch.*`    | suportado |
| LaunchSubstitution.environment_variable | sim |  sim |    sim | `environment_substitution.launch.*` | suportado |
| Estabilidade de hash local              | n/a |  n/a |    sim | `stable_id_a/b.launch.py`           | suportado |

Resultado:

```text
PASS: 28
FAIL: 0
```

---

### Cobertura ainda em aberto

Apesar dos testes atuais passarem, isto não significa suporte completo a todo o ROS 2 launch nem a todo o HAROS Layer 2.

Os testes atuais cobrem os principais action types, várias substitutions, conditions simples e compostas, includes com argumentos, grupos e namespaces.

Ainda falta testar ou clarificar:

| Área                                   | Estado                    | Observação                                                                                                  |
| -------------------------------------- | ------------------------- | ----------------------------------------------------------------------------------------------------------- |
| `LaunchSubstitution.expression`        | por testar                | Ainda não há teste específico para expressões genéricas.                                                    |
| Includes transitivos                   | por testar                | O include é representado, mas não há resolução recursiva completa.                                          |
| Self-inclusion                         | por testar                | Ainda não há teste que detete include circular.                                                             |
| Validação de ciclos na árvore de ações | parcialmente coberto      | O `Layer2Validator` tem validação, mas faltam testes negativos dedicados.                                   |
| Ações órfãs                            | parcialmente coberto      | Falta teste negativo com action fora de `launch_sequence` e sem parent.                                     |
| IDs inválidos                          | parcialmente coberto      | SHACL valida o padrão dos IDs RDF, mas ainda faltam testes negativos diretos.                               |
| Colisões de hash / ordinal `#0`, `#1`  | por testar                | Ainda não há teste para ações semanticamente iguais no mesmo ficheiro.                                      |
| Estabilidade forte dos IDs             | parcial                   | Foi testada estabilidade de hash local para dois ficheiros Python equivalentes.                             |
| `set_env`                              | parcial                   | Atualmente é modelado como `SetParameterAction`, não como entidade própria de ambiente.                     |
| `argument_mappings`                    | parcial                   | São exportados para RDF como `ros:Parameter`; ainda não há entidade própria para mapeamentos de argumentos. |
| Substitutions em RDF                   | parcial                   | Algumas substitutions são materializadas como strings; ainda não são sempre nós RDF próprios.               |
| `OpaqueFunction`                       | fora do subconjunto atual | Python dinâmico complexo ainda não é suportado.                                                             |
| Loops dependentes de runtime           | fora do subconjunto atual | Não há abstract interpretation completa para estes casos.                                                   |
| Execução sandboxed fallback            | não implementado          | O documento HAROS menciona esta possibilidade, mas o projeto ainda não a implementa.                        |
| Publishers/subscribers reais           | suportado via camada runtime anotada | Launch files não indicam necessariamente os topics publicados/subscritos; a informação vem de `node_interfaces/*.communication.yaml` e é cruzada com os NodeAction do Layer 2 e remappings.                       |
| Integração real com HAROS              | por fazer                 | O JSON está próximo do Layer 2, mas ainda não foi consumido diretamente pelo HAROS.                         |
| Regras arquiteturais ROS               | por fazer                 | Já existem regras de comunicação sobre node isolado, publisher sem subscriber, subscriber sem publisher, múltiplos publishers e QoS reliability; continuam fora do escopo casos mais avançados sem informação adicional dos nodes.                  |

---

### Interpretação dos resultados

Os resultados atuais indicam que o extrator já produz uma representação Layer 2 consistente para um subconjunto relevante e testado de ROS 2 launch.

A matriz não afirma suporte completo. Ela documenta, com testes reproduzíveis, o que está atualmente suportado, o que está parcialmente suportado e o que continua fora do escopo ou por testar.

Esta distinção é importante porque os exemplos canónicos são controlados e focados em features específicas. Eles servem para validar a cobertura do modelo intermédio antes de avançar para análises mais sofisticadas.

A fase RDF/SHACL mostra que o JSON Layer 2 já pode ser transformado numa representação baseada em conhecimento e validado por regras declarativas.

---

## 10. Validação Layer 2

O validador (`Layer2Validator`) verifica 9 regras da especificação:

1. **actions_map_consistency** — chaves do mapa correspondem aos IDs;
2. **sequence_validity** — IDs na sequência existem no mapa;
3. **reachability** — acções são alcançáveis;
4. **no_orphans** — sem acções órfãs;
5. **id_format** — IDs seguem `la:<file>:<hash>#<ordinal>`;
6. **no_cycles** — árvore acíclica;
7. **scope_actions_only** — só `group`, `push_namespace` e `include` têm children;
8. **node_required_fields** — `NodeAction` tem package e executable;
9. **include_required_fields** — `IncludeAction` tem `included_launch_id`.

---

## 11. Exportação RDF/Turtle e validação SHACL

O projecto exporta o modelo Layer 2 para RDF/Turtle:

```bash
python3 scripts/ontology/export_layer2_to_rdf.py output/robot.launch.layer2.json output/rdf/robot.launch.layer2.ttl
```

O RDF pode ser validado com SHACL:

```bash
python3 scripts/ontology/validate_all_rdf.py
```

Também existem issues detectados directamente sobre o grafo RDF através de queries SPARQL:

```bash
python3 scripts/ontology/run_ontology_issues.py output/rdf/robot.launch.layer2.ttl
```

Output:

```bash
output/issues/robot.launch.ontology.issues.json
```

Para correr a pipeline ontológica completa sobre todos os JSONs Layer 2:

```bash
python3 scripts/ontology/run_all_ontology_pipeline.py output
```

Esta pipeline:

1. encontra todos os ficheiros `*.layer2.json`;
2. gera RDF/Turtle em `output/rdf/`;
3. executa queries SPARQL;
4. converte os resultados em issues Layer 6;
5. guarda os resultados em `output/issues/*.ontology.issues.json`.

A ontologia também foi estendida para representar comunicação runtime. Para isso foram adicionadas classes e propriedades para `RuntimeArchitecture`, `RuntimeNode`, `Topic`, `Publication`, `Subscription` e `QoSProfile`. Esta parte é usada pela pipeline de comunicação e pelas queries SPARQL em `ontology/queries/communication/`.

---

### Exportação RDF/Turtle e issues ontológicos

Para responder à parte ontológica do projecto, o modelo Layer 2 pode ser exportado para RDF/Turtle. Esta exportação permite correr validações SHACL e queries SPARQL sobre o grafo.

#### Exportação RDF

O script principal é:

```bash
python3 scripts/ontology/export_layer2_to_rdf.py output/robot.launch.layer2.json output/rdf/robot.launch.layer2.ttl
```

O RDF gerado representa, entre outros elementos:

```text
ros:LaunchDescription
ros:LaunchAction
ros:NodeAction
ros:DeclareArgumentAction
ros:IncludeAction
ros:GroupAction
ros:Parameter
ros:Remapping
ros:Condition
ros:Provenance
```

Cada action recebe propriedades como:

```text
ros:hasActionId
ros:hasPackage
ros:hasExecutable
ros:hasNodeName
ros:hasNamespace
ros:hasParameter
ros:hasRemapping
ros:hasCondition
ros:hasProvenance
```

E a proveniência é exportada para o grafo com informação como:

```text
ros:hasSourceFile
ros:hasConfidence
```

#### Validação SHACL

As shapes SHACL encontram-se em:

```text
ontology/shapes.ttl
```

A validação pode ser executada com:

```bash
python3 scripts/ontology/validate_all_rdf.py
```

As shapes verificam propriedades estruturais do RDF, por exemplo:

```text
LaunchDescription tem formato e launch_file_id
NodeAction tem package e executable
DeclareArgumentAction tem nome
IncludeAction referencia o launch incluído
Remapping tem origem e destino
Parameter tem nome
```

#### Queries SPARQL para issues ontológicos

Além dos issues estruturais gerados directamente sobre o `LaunchDescription`, o projecto tem uma segunda backend de análise: issues detectados por queries SPARQL sobre o RDF.

As queries vivem em:

```text
ontology/queries/*.rq
```

Exemplos:

```text
node_no_name.rq
include_unresolved.rq
arg_no_default.rq
action_without_provenance.rq
```

O detector ontológico é:

```text
issues/ontology_detector.py
```

E pode ser executado com:

```bash
python3 scripts/ontology/run_ontology_issues.py output/rdf/robot.launch.layer2.ttl
```

O output é guardado em:

```text
output/issues/<nome>.ontology.issues.json
```

Exemplo de fluxo:

```text
output/robot.launch.layer2.json
        │
        ▼
output/rdf/robot.launch.layer2.ttl
        │
        ▼
SPARQL queries
        │
        ▼
output/issues/robot.launch.ontology.issues.json
```

#### Diferença entre issues estruturais e issues ontológicos

Existem agora duas fontes de análise:

| Tipo | Entrada | Motor | Output |
|---|---|---|---|
| Issues estruturais | `LaunchDescription` em memória | Python | `output/issues/*.issues.json` |
| Issues ontológicos | RDF/Turtle | SPARQL via `rdflib` | `output/issues/*.ontology.issues.json` |

Alguns issues aparecem nos dois lados, como `node_no_name` ou `include_unresolved`. Outros são mais naturais no modelo estrutural, como `namespace_implicit`, porque exigem raciocínio sobre escopo e herança de namespace que ainda não está totalmente materializado no RDF.

---

### Ontologia RDF/OWL e validação SHACL

Foi criada uma primeira ontologia para representar o subconjunto Layer 2 extraído pelo projeto.

Ficheiros:

`ontology/ros_launch.ttl`
`ontology/shapes.ttl`

A ontologia representa:

| Conceito Layer 2      | Representação RDF/OWL       |
| --------------------- | --------------------------- |
| LaunchDescription     | `ros:LaunchDescription`     |
| LaunchAction          | `ros:LaunchAction`          |
| NodeAction            | `ros:NodeAction`            |
| DeclareArgumentAction | `ros:DeclareArgumentAction` |
| SetParameterAction    | `ros:SetParameterAction`    |
| PushNamespaceAction   | `ros:PushNamespaceAction`   |
| IncludeAction         | `ros:IncludeAction`         |
| GroupAction           | `ros:GroupAction`           |
| Parameter             | `ros:Parameter`             |
| Remapping             | `ros:Remapping`             |
| Condition             | `ros:Condition`             |
| Provenance            | `ros:Provenance`            |

Também foram definidos scripts para exportar JSON Layer 2 para RDF/Turtle e validar o RDF com SHACL:

`scripts/ontology/export_layer2_to_rdf.py`
`scripts/ontology/export_all_layer2_to_rdf.py`
`scripts/ontology/validate_rdf.py`
`scripts/ontology/validate_all_rdf.py`

Resultado atual da exportação RDF:

```text
EXPORTADOS: 70
FALHARAM:   0
```

Resultado atual da validação SHACL:

```text
VÁLIDOS:   70
INVÁLIDOS: 0
```

Isto valida o pipeline:

launch file → Layer2 JSON → RDF/Turtle → SHACL

---

### Regras SHACL atuais

As regras SHACL atuais verificam propriedades estruturais básicas:

| Regra                                                  | Estado       |
| ------------------------------------------------------ | ------------ |
| LaunchDescription tem `hasLaunchFileId`                | implementado |
| LaunchDescription tem `hasFormat`                      | implementado |
| LaunchDescription tem pelo menos uma action            | implementado |
| LaunchAction tem `hasActionId`                         | implementado |
| Action ID segue padrão `la:<file_id>:<hash>#<ordinal>` | implementado |
| NodeAction tem package                                 | implementado |
| NodeAction tem executable                              | implementado |
| DeclareArgumentAction tem nome                         | implementado |
| SetParameterAction tem parâmetro                       | implementado |
| IncludeAction referencia launch incluído               | implementado |
| Remapping tem origem e destino                         | implementado |
| Parameter tem nome                                     | implementado |

---

---

## 12. Issue Detection — Layer 6

O projecto gera issues em formato inspirado no **HAROS Layer 6**. Cada issue contém:

```json
{
  "id": "issue_file_robot_001",
  "severity": "warning",
  "category": "architecture",
  "description": "Include com path dinâmico não resolvível estaticamente.",
  "affected_entities": [
    {"type": "include", "id": "la:file_robot:67b5c1be#0"}
  ],
  "analysis_tool": "ProjetoEL-extractor",
  "analysis_timestamp": "2026-05-12T16:33:05Z",
  "location": {"file_path": "examples/real-python/robot.launch.py"},
  "metadata": {
    "issue_key": "include_unresolved",
    "title": "Include com path dinâmico",
    "recommendation": "Resolver este include através de configuração concreta, execução instrumentada ou anotação."
  }
}
```

### Catálogo externo

As definições dos issues vivem em:

```bash
issues/catalog.yaml
```

O catálogo define severidade, categoria, título, descrição, recomendação e tipo de entidade. Isto permite ajustar a política de análise sem alterar o código Python.

### Issues estruturais

Os issues estruturais são detectados sobre o modelo Layer 2 em memória:

```bash
python3 main.py python examples/real-python/robot.launch.py
```

Output:

```bash
output/issues/robot.launch.issues.json
```

Exemplos de issues estruturais:

- `node_no_name`
- `include_unresolved`
- `arg_no_default`
- `arg_orphan`
- `node_runtime_condition`
- `opaque_symbolic_node`
- `namespace_implicit`
- `include_self`

---

### Detector estrutural Layer 6

O `IssueDetector` analisa o `LaunchDescription` Layer 2 e produz `Issue` conforme a especificação `layer6.pdf`. É executado automaticamente após a validação Layer 2.

Na versão actual, a detecção foi separada da definição dos issues:

- `issues/detector.py` detecta padrões estruturais no `LaunchDescription`;
- `models/layer6.py` define `Issue` e `ElementRef`;
- `issues/io.py` escreve os issues em JSON;
- `issues/catalog.yaml` contém as definições externas dos issues.

Isto evita manter severidades, categorias, descrições e recomendações hardcoded no detector. O código detecta a condição, mas a descrição formal do issue vem do catálogo YAML.

#### Estrutura de um `Issue`

Os issues estruturais são guardados em:

```text
output/issues/<nome>.issues.json
```

Exemplo simplificado:

```json
{
  "analysis_timestamp": "2026-05-12T16:33:05.110602Z",
  "issue_count": 1,
  "issues": [
    {
      "id": "issue_file_spawn_001",
      "severity": "warning",
      "category": "architecture",
      "description": "Include com path dinâmico não resolvível estaticamente - o ficheiro incluído só é determinado em runtime.",
      "affected_entities": [
        {"type": "include", "id": "la:file_spawn:8e31550a#0"}
      ],
      "analysis_tool": "ProjetoEL-extractor",
      "analysis_timestamp": "2026-05-12T16:33:05.110602Z",
      "location": {"file_path": "examples/real-python/spawn_robot.launch.py"},
      "metadata": {
        "included_launch_id": "launch_desc_file_os_path_join_...",
        "issue_key": "include_unresolved",
        "title": "Include com path dinâmico",
        "recommendation": "Resolver este include através de configuração concreta, execução instrumentada ou anotação."
      }
    }
  ]
}
```

O timestamp é comum a todos os issues gerados na mesma execução, para facilitar reprodutibilidade e comparação.

#### Exemplo de definição em `issues/catalog.yaml`

```yaml
include_unresolved:
  enabled: true
  severity: warning
  category: architecture
  title: "Include com path dinâmico"
  description: "Include com path dinâmico não resolvível estaticamente - o ficheiro incluído só é determinado em runtime."
  recommendation: "Resolver este include através de configuração concreta, execução instrumentada ou anotação."
  entity_type: include
```

#### Issues detectáveis no Layer 2

##### `node_no_name` — `[INFO]`

```python
Node(package='ros_gz_sim', executable='create')  # sem name=
```

Detectado quando `action.name is None`. O node vai usar o `executable` como nome por omissão em runtime — pode causar conflitos se houver dois nodes com o mesmo executable.

##### `node_runtime_condition` — `[INFO]`

```python
if has_resource('packages', 'image_view'):
    composable_nodes.append(ComposableNode(...))
```

Detectado quando a condição contém `has_resource`. O node só é instanciado se o package existir no sistema — informação de runtime.

##### `opaque_symbolic_node` — `[WARNING]`

```python
for i in range(0, N):
    ld.add_action(Node(package="demo_nodes_cpp", executable="talker"))
```

Detectado quando a condição contém `for` e `range`. O número exacto de instâncias depende do valor de `N` em runtime.

##### `include_unresolved` — `[WARNING]`

```python
IncludeLaunchDescription(
    PythonLaunchDescriptionSource(
        os.path.join(pkg_var, 'launch', 'world.launch.py')
    )
)
```

Detectado quando o `included_launch_id` contém `os_path_join` ou `type____var` — o path não foi resolvível estaticamente.

##### `arg_no_default` — `[WARNING]`

```python
DeclareLaunchArgument('num_pairs')  # sem default_value=
```

Detectado quando `action.default_value is None`. O arg tem de ser sempre fornecido ao invocar o launch file.

##### `arg_orphan` — `[INFO]`

```python
declared_args = []
declared_args.append(DeclareLaunchArgument("num_node_pairs", default_value="1"))
ld = LaunchDescription()  # declared_args nunca adicionado!
```

Detectado quando `action.provenance.confidence < 0.9` — o arg foi extraído por `_extract_orphan_args` porque nunca foi adicionado explicitamente ao `LaunchDescription`.

##### `namespace_implicit` — `[INFO]`

Detectado quando existe um `PushNamespaceAction` no `LaunchDescription` e um `NodeAction` não tem `namespace` explícito — o node vai herdar o namespace do contexto em runtime.

##### `include_self` — `[ERROR]`

Detectado quando `action.included_launch_id == ld.id` — o launch file inclui-se a si próprio, criando um ciclo infinito.

#### Limitações — o que não é detectável no Layer 2

Os issues mais graves do `layer6.pdf` requerem informação de camadas superiores:

| Issue | Requer | Camada |
|---|---|---|
| QoS incompatibility | Tópicos publicados/subscritos e seus perfis QoS | Layer 1 + Layer 4 |
| Type mismatch | Tipos de mensagens de cada tópico | Layer 1 |
| Orphan publisher | Grafo completo de comunicação | Layer 4 |
| Rate mismatch | Taxas de publicação | Layer 1/4 |

Estes issues só podem ser detectados pelo HAROS após resolver o Layer 2 em instâncias concretas (Layer 3/4) e cruzar com a informação dos nodes (Layer 1).

---

## 13. Arquitetura Runtime e Grafo de Comunicação

A Layer 2 extraída dos launch files representa o programa simbólico de lançamento: que nodes são lançados, com que package, executable, name, namespace, parâmetros, remappings, includes e condições. No entanto, um launch file ROS2 normalmente **não declara explicitamente** que topics cada node publica ou subscreve.

Por exemplo, um launch file pode lançar:

```python
Node(
    package="turtlebot3_node",
    executable="turtlebot3_ros"
)
```

mas esta linha não diz que o node publica `/odom` ou `/tf`, nem que subscreve `/cmd_vel`. Essa informação pertence ao node individual, isto é, ao código do node, à documentação do package, a ficheiros de configuração, a análise estática do código ou a observação em runtime.

Por isso, a estratégia usada nesta fase segue a ideia:

```text
arquitectura de comunicação =
    informação dos nós individuais
  + informação dos nodes lançados pelo launch file
  + remappings definidos no launch file
```

### Papel dos ficheiros node_interfaces/*.communication.yaml

Os ficheiros YAML em node_interfaces/ *não representam a arquitectura final*. Representam a interface conhecida dos nodes individuais.

Ou seja, dizem:

- que node se pretende anotar;
- como encontrar esse node dentro do Layer 2;
- que topics esse node publica;
- que topics esse node subscreve;
- que tipo de mensagem usa cada topic;
- que QoS é esperado em cada publisher/subscriber.

Exemplo simplificado:

```yaml
architecture_id: robot_runtime_architecture
configuration_id: default

nodes:
  - selector:
      package: turtlebot3_node
      executable: turtlebot3_ros

    runtime_name: /turtlebot3_ros

    publishes:
      - topic: /odom
        msg_type: nav_msgs/msg/Odometry
        qos:
          reliability: reliable
          durability: volatile
          history: keep_last
          depth: 10

      - topic: /tf
        msg_type: tf2_msgs/msg/TFMessage
        qos:
          reliability: reliable
          durability: volatile
          history: keep_last
          depth: 10

    subscribes:
      - topic: /cmd_vel
        msg_type: geometry_msgs/msg/Twist
        qos:
          reliability: reliable
          durability: volatile
          history: keep_last
          depth: 10
```

Esta informação pode vir de várias fontes:

```text
1. documentação do package ROS2;
2. código fonte do node;
3. ficheiros de configuração do node;
4. conhecimento do domínio;
5. output de ferramentas runtime como ros2 node info;
6. anotações manuais controladas para teste.
```

No projecto, esta informação é fornecida em YAML para manter a pipeline reproduzível, explícita e testável. O YAML funciona como substituto de uma futura Layer 1 ou de uma futura análise automática dos nodes individuais.

### Validação da interface anotada de `robot.launch.py`

No caso de `robot.launch.py`, a interface em `node_interfaces/robot.communication.yaml`
foi tratada como anotação manual parcialmente validada. Como não foi possível executar
ROS2 neste ambiente, a validação não foi feita por introspecção runtime.

A validação ideal seria feita com:

```bash
ros2 node info /turtlebot3_ros
ros2 topic info -v /cmd_vel
ros2 topic info -v /odom
ros2 topic info -v /tf
```

ou por análise estática do código fonte dos packages envolvidos.

A hipótese de `/scan` pertencer directamente à interface de `/turtlebot3_ros` teria de ser validada separadamente, porque pode pertencer a outro node/driver, como um node de LIDAR ou obstacle detection.

| Entrada                                         | Estado                         | Comentário                                                                                                                                                                                                         |
| ----------------------------------------------- | ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `/cmd_vel` como subscrição de `/turtlebot3_ros` | Mantido                        | A documentação TurtleBot3 indica que o TurtleBot3 Node subscreve `cmd_vel` para controlar o movimento. Em algumas versões, o tipo pode ser `TwistStamped` em vez de `Twist`.                                       |
| `/odom` como publicação de `/turtlebot3_ros`    | Mantido com validação pendente | O bringup TurtleBot3 expõe `/odom`, mas a associação exacta ao node/processo deve ser confirmada por runtime ou código fonte.                                                                                      |
| `/tf` como publicação de `/turtlebot3_ros`      | Mantido com validação pendente | O bringup TurtleBot3 expõe `/tf`, mas a documentação também menciona componentes internos como `diff_drive_controller`; a associação exacta deve ser confirmada.                                                   |
| `/scan` como subscrição de `/turtlebot3_ros`    | Removido da anotação final     | A documentação associa a subscrição de `/scan` ao `turtlebot3_obstacle_detection`, não directamente ao `turtlebot3_node`. Por isso, não foi mantido como interface real de `turtlebot3_ros` sem validação runtime. |

Assim, o exemplo `robot.launch.py` é usado como caso real parcialmente anotado, enquanto `communication_demo.launch.py` é o exemplo controlado usado para demonstrar todos os issues de comunicação suportados.

### Construção da RuntimeArchitecture

O script principal é:

```bash
python3 scripts/communication/build_runtime_architecture.py \
  output/robot.launch.layer2.json \
  node_interfaces/robot.communication.yaml
```

ou, usando a pipeline completa:

```bash
python3 scripts/communication/run_communication_pipeline.py \
  output/robot.launch.layer2.json \
  node_interfaces/robot.communication.yaml
```

O processo é:

```text
1. carregar o JSON Layer 2;
2. carregar o YAML com a interface dos nodes individuais;
3. procurar, no Layer 2, os NodeAction que correspondem aos selectors do YAML;
4. construir RuntimeNode para cada node realmente lançado;
5. aplicar name e namespace;
6. aplicar os remappings declarados no launch file;
7. criar Topic, Publication, Subscription e QoSProfile;
8. gerar RuntimeArchitecture em JSON;
9. exportar a arquitectura para RDF/Turtle;
10. executar queries SPARQL de comunicação.
```

### Aplicação de remappings

Os remappings pertencem ao launch file. Por isso, a interface do node é escrita em termos dos topics que o node usa, mas a arquitectura runtime deve reflectir os nomes depois de aplicados os remappings.

Exemplo:

```python
Node(
    package="demo_pkg",
    executable="talker",
    remappings=[
        ("/chatter", "/robot/chatter")
    ]
)
```

Se o YAML disser que o node publica **/chatter**, a RuntimeArchitecture deve registar a publicação em **/robot/chatter**, porque esse é o topic efectivo após o launch file ser aplicado.

Isto é a ligação entre:

```text
informação do node individual → /chatter
launch file → remap /chatter para /robot/chatter
arquitectura runtime → publisher em /robot/chatter
```

### Modelo RuntimeArchitecture

A arquitectura runtime gerada é guardada em:

```text
output/architecture/*.architecture.json
```

O modelo contém:

```text
RuntimeArchitecture
RuntimeNode
Topic
Publication
Subscription
QoSProfile
```

Exemplo de estrutura:

```json
{
  "id": "robot_runtime_architecture",
  "configuration_id": "default",
  "source_layer2_path": "output/robot.launch.layer2.json",
  "nodes": {
    "runtime_node:...": {
      "package": "turtlebot3_node",
      "executable": "turtlebot3_ros",
      "runtime_name": "/turtlebot3_ros"
    }
  },
  "topics": {
    "topic:odom": {
      "name": "/odom",
      "msg_type": "nav_msgs/msg/Odometry"
    }
  },
  "publications": {},
  "subscriptions": {}
}
```

### Exportação RDF da comunicação

A RuntimeArchitecture também é exportada para RDF/Turtle:

```text
output/rdf/architecture/*.architecture.ttl
```

A ontologia representa entidades de comunicação com as classes:

```text
ros:RuntimeArchitecture
ros:RuntimeNode
ros:Topic
ros:Publication
ros:Subscription
ros:QoSProfile
```

E relações como:

```text
ros:publishes
ros:subscribes
ros:onTopic
ros:hasPublisher
ros:hasSubscriber
ros:hasQoS
ros:qosReliability
ros:qosDurability
ros:qosHistory
ros:qosDepth
```

### Issues de comunicação

Depois de exportada a arquitectura para RDF, são executadas queries SPARQL sobre o grafo de comunicação.

Issues actualmente suportados:

| Issue                          | Descrição                                                         |
| ------------------------------ | ----------------------------------------------------------------- |
| `isolated_node`                | Node runtime sem publishers nem subscribers anotados              |
| `publisher_without_subscriber` | Topic publicado sem subscribers conhecidos                        |
| `subscriber_without_publisher` | Topic subscrito sem publishers conhecidos                         |
| `topic_multiple_publishers`    | Topic com mais do que um publisher                                |
| `qos_reliability_mismatch`     | Publisher `best_effort` ligado a subscriber que requer `reliable` |

Exemplo de execução:

```bash
python3 scripts/communication/run_communication_pipeline.py \
  output/communication_demo.launch.layer2.json \
  node_interfaces/communication_demo.communication.yaml
```

Resultado esperado no exemplo controlado:

```text
[OK] Nodes: 8
[OK] Topics: 4
[OK] Publications: 4
[OK] Subscriptions: 3
[OK] Issues de comunicação: 5
  [WARNING ] Node '/isolated' não publica nem subscreve tópicos na arquitetura anotada.
  [WARNING ] Topic '/lonely_pub' publicado por '/lonely_publisher' não tem subscribers anotados.
  [WARNING ] Topic '/lonely_sub' subscrito por '/lonely_subscriber' não tem publishers anotados.
  [WARNING ] Topic '/shared_topic' tem 2 publishers anotados: /talker_b, /talker_a.
  [ERROR   ] Topic '/qos_topic' tem publisher '/qos_publisher' com reliability 'best_effort' mas subscriber '/qos_subscriber' requer 'reliable'.
```

### Exemplo controlado de comunicação

Foi criado um exemplo específico para validar esta camada:

```text
examples/communication/communication_demo.launch.py
node_interfaces/communication_demo.communication.yaml
```

Este exemplo foi desenhado para exercitar os principais casos de comunicação:

```text
/talker_a e /talker_b publicam no mesmo tópico
/shared_listener subscreve esse tópico
/qos_publisher e /qos_subscriber têm QoS incompatível
/isolated não comunica com ninguém
/lonely_publisher publica sem subscriber
/lonely_subscriber subscreve sem publisher
```

A pipeline permite aplicar a mesma metodologia tanto a exemplos controlados como a launch files reais. No exemplo controlado, a informação em `node_interfaces/communication_demo.communication.yaml` não pretende representar um sistema real completo; serve para validar que o modelo consegue representar publicações, subscrições, múltiplos publishers, ausência de pares de comunicação e incompatibilidade de QoS.

### Execução separada da pipeline de comunicação

O script `run_communication_pipeline.py` agrega três fases, mas estas também podem ser executadas separadamente:

```bash
python3 scripts/communication/build_runtime_architecture.py   output/robot.launch.layer2.json   node_interfaces/robot.communication.yaml

python3 scripts/communication/export_architecture_to_rdf.py   output/architecture/robot.launch.architecture.json

python3 scripts/communication/run_communication_issues.py   output/rdf/architecture/robot.launch.architecture.ttl
```

Isto deixa claro que a análise de comunicação é construída por etapas: primeiro a arquitectura runtime em JSON, depois a exportação RDF/Turtle, e finalmente as queries SPARQL de comunicação.

### Limitação importante

A qualidade dos issues de comunicação depende da qualidade das interfaces fornecidas em **node_interfaces/**.

Se faltar anotar um subscriber, pode aparecer um **publisher_without_subscriber**. Se faltar anotar um publisher, pode aparecer um **subscriber_without_publisher**.

Portanto, estes issues devem ser interpretados como:

```text
“segundo a arquitectura anotada conhecida, este topic está sem publisher/subscriber”
```

e não como prova absoluta de que o sistema real em runtime tem esse erro.

Esta decisão é intencional: mantém clara a separação entre a informação extraída do launch file e a informação conhecida sobre os nodes individuais.

---

### Decisão metodológica complementar

A camada de comunicação foi mantida separada do Layer 2 por três razões:

**1. Separação semântica**
O Layer 2 representa o launch file. A arquitectura runtime representa uma configuração de comunicação. São níveis diferentes de informação.

**2. Rastreabilidade**
Cada RuntimeNode mantém referência ao action_id do NodeAction original. Assim, é possível ligar um problema de comunicação ao node que veio do launch file.

**3. Extensibilidade**
A informação de comunicação pode vir de anotações YAML, de introspecção ROS2, de documentação, ou futuramente de análise de código. O modelo runtime não depende da origem da informação.

Esta abordagem evita fingir que a comunicação foi inferida automaticamente quando ela foi, na verdade, fornecida por conhecimento auxiliar.

---

## 14. Backend GraphDB

Além da execução local com `rdflib`, o projecto suporta execução das queries SPARQL num repositório GraphDB.

O GraphDB não substitui o pipeline local. Funciona como backend persistente para carregar todos os RDFs gerados e executar queries globais sobre o conjunto completo.

### Fluxo

```text
output/rdf/*.ttl
output/rdf/architecture/*.ttl
        │
        ▼
GraphDB repository
        │
        ▼
SPARQL endpoint
        │
        ▼
GraphDBIssueDetector
        │
        ▼
output/issues/graphdb.issues.json
```

### Upload dos RDFs

```bash
python3 scripts/graphdb/graphdb_clear.py --repo haros
python3 scripts/graphdb/graphdb_upload.py output/rdf --repo haros
```

O upload percorre recursivamente output/rdf/, por isso carrega tanto os RDFs Layer 2 como os RDFs de arquitectura runtime em:

```text
output/rdf/architecture/
```

### Query manual

```bash
python3 scripts/graphdb/graphdb_query.py \
  ontology/queries/communication/qos_reliability_mismatch.rq \
  --repo haros
```

### Geração de issues GraphDB

```bash
python3 scripts/graphdb/run_graphdb_issues.py --repo haros
```

O output é:

```text
output/issues/graphdb.issues.json
```

Actualmente o GraphDB executa dois grupos de queries:

```text
ontology/queries/*.rq
ontology/queries/communication/*.rq
```

Assim, consegue detectar issues estruturais Layer 2 e issues de comunicação runtime no mesmo repositório.

### Reutilização das queries

A lógica das queries é partilhada entre a execução local e o GraphDB. As queries SPARQL em `ontology/queries/` e `ontology/queries/communication/` podem ser executadas localmente com `rdflib` ou remotamente sobre o endpoint SPARQL do GraphDB. Assim, o que muda é apenas o backend de execução, não a definição declarativa dos issues.

| Backend | Como funciona | Resultado |
|---|---|---|
| `rdflib` | carrega um `.ttl` em memória | issues ontológicos ou de comunicação por ficheiro |
| GraphDB | consulta o repositório completo | issues estruturais e de comunicação sobre todos os RDFs carregados |

### Scripts GraphDB

A integração GraphDB foi mantida em scripts independentes para não tornar a demo principal dependente de um serviço externo:

| Script | Função |
|---|---|
| `scripts/graphdb/graphdb_clear.py` | limpa os dados RDF do repositório |
| `scripts/graphdb/graphdb_upload.py` | carrega ficheiros `.ttl`, incluindo subpastas como `output/rdf/architecture/` |
| `scripts/graphdb/graphdb_query.py` | executa uma query SPARQL manual no endpoint GraphDB |
| `scripts/graphdb/run_graphdb_issues.py` | executa as queries configuradas e gera `output/issues/graphdb.issues.json` |
| `scripts/demos/demo_graphdb.sh` | executa a sequência de limpeza, upload, query de teste e geração de issues GraphDB |

---

### Conversão para Issues Layer 6 no GraphDB

Os resultados devolvidos pelo GraphDB em formato SPARQL JSON são convertidos por:

```text 
issues/graphdb_detector.py
```

Este detector segue a mesma lógica do OntologyIssueDetector local:

- 1.carrega a definição do issue a partir de issues/catalog.yaml;
- 2.executa a query SPARQL correspondente;
- 3.transforma cada linha de resultado num Issue;
- 4.identifica a entidade afectada através de action_id;
- 5.preserva metadados como source_file, package, executable ou included_launch_id;
- 6.marca a origem do issue como graphdb.

Exemplo de metadata:

```json
{
  "issue_key": "node_no_name",
  "title": "Node sem nome explícito",
  "source": "graphdb",
  "recommendation": "Definir explicitamente o campo name quando for importante garantir nomes estáveis."
}
```

O ficheiro final é:

```text
output/issues/graphdb.issues.json
```

### Papel do GraphDB na arquitectura

O GraphDB não substitui o Layer 2 nem o detector local. Ele acrescenta uma backend persistente para análise semântica. A pipeline passa a ter três níveis complementares de análise:

```text
1. Validação Layer 2
   Verifica a consistência estrutural do modelo em memória.

2. Issues estruturais
   Detectam padrões directamente no LaunchDescription.

3. Issues ontológicos
   Executam queries SPARQL sobre RDF, localmente ou no GraphDB.
```

A vantagem do GraphDB é permitir análise global sobre todos os grafos RDF carregados. Isto é especialmente útil para queries que dependem de cruzar informação entre vários launch files ou para exploração interactiva no Workbench.

---

### Relação com a análise de comunicação

A integração GraphDB foi inicialmente aplicada ao RDF gerado a partir do Layer 2. Esse RDF contém launch descriptions, actions, includes, nodes simbólicos, parâmetros, remappings, condições e proveniência. Com essa informação, o GraphDB consegue detectar issues estruturais e ontológicos sobre o modelo de launch, como nodes sem nome explícito ou includes dinâmicos.

A análise de comunicação foi implementada numa camada posterior, através de uma arquitectura runtime anotada. Essa arquitectura já representa explicitamente:

```text
ros:RuntimeArchitecture
ros:RuntimeNode
ros:Topic
ros:Publication
ros:Subscription
ros:QoSProfile
ros:publishes
ros:subscribes
ros:onTopic
ros:hasQoS
```

Assim, o projecto passa a ter duas famílias de grafos RDF:

| Grafo RDF        | Origem                       | Tipo de análise                                          |
| ---------------- | ---------------------------- | -------------------------------------------------------- |
| Layer 2 RDF      | JSON Layer 2                 | estrutura de launch, actions, includes, nodes simbólicos |
| Architecture RDF | JSON de arquitectura runtime | comunicação, topics, publishers, subscribers, QoS        |

Neste momento, os issues de comunicação são executados localmente sobre o RDF de arquitectura com rdflib, usando queries SPARQL próprias. O GraphDB continua preparado para receber também estes RDFs de arquitectura, permitindo no futuro executar as mesmas queries de comunicação sobre um triplestore persistente.

---

## 15. Pipeline Operacional e Demo

Para automatizar a execução completa, foi criado:

```text
scripts/ontology/run_all_ontology_pipeline.py
```

Este script percorre todos os ficheiros `*.layer2.json`, gera os respectivos RDFs e corre a análise ontológica sobre cada um.

```bash
python3 scripts/ontology/run_all_ontology_pipeline.py output
```

O script faz:

```text
1. encontra todos os JSONs Layer 2
2. exporta cada JSON para RDF/Turtle
3. corre queries SPARQL sobre cada RDF
4. gera issues ontológicos em JSON
5. apresenta um resumo final
```

O `demo.sh` foi actualizado para executar a cadeia completa:

```text
1. limpeza de outputs antigos
2. compilação Python
3. testes Layer 2 mínimos
4. testes de cobertura HAROS Layer 2
5. testes nos exemplos reais Python
6. pipeline ontológico completo
7. validação SHACL
8. resumo dos outputs gerados
```

A execução completa gera:

```text
12 JSONs Layer 2 dos exemplos reais
58 JSONs Layer 2 dos testes mínimos e de cobertura
70 RDFs Layer 2
12 JSONs de issues estruturais
70 JSONs de issues ontológicos
```

Com isto, a demonstração cobre a cadeia completa desde a extracção sintáctica até à análise ontológica:

```text
launch file
  → Layer 2 JSON
  → issues estruturais Layer 6
  → RDF/Turtle
  → SHACL
  → SPARQL
  → issues ontológicos Layer 6
```

Esta estrutura também prepara a integração com GraphDB: os ficheiros `output/rdf/*.ttl` já podem ser carregados num triplestore e as queries SPARQL em `ontology/queries/` podem ser reutilizadas sobre um endpoint SPARQL externo.

---

## 16. Resultados de Teste

Testado em **12 launch files Python reais**:

| Ficheiro | Acções | Nodes | Args | Includes | Validação |
|---|--:|--:|--:|--:|:-:|
| `bringup_launch.py` | 25 | 1 | 17 | 5 | ✓ |
| `camera.launch.py` | 8 | 3 | 5 | 0 | ✓ |
| `multi_nodes_no_opaque.launch.py` | 1 | 0 | 1 | 0 | ✓ |
| `navigation_launch.py` | 41 | 24 | 12 | 0 | ✓ |
| `on_shutdown_example.launch.py` | 2 | 1 | 0 | 0 | ✓ |
| `opaque_multi_nodes.launch.py` | 3 | 2 | 1 | 0 | ✓ |
| `opaque_multi_nodes_inplace.launch.py` | 3 | 2 | 1 | 0 | ✓ |
| `robot.launch.py` | 8 | 1 | 4 | 2 | ✓ |
| `rviz2.launch.py` | 1 | 1 | 0 | 0 | ✓ |
| `spawn_robot.launch.py` | 14 | 7 | 6 | 1 | ✓ |
| `topic_params.launch.py` | 3 | 2 | 0 | 1 | ✓ |
| `turtlebot3_state_publisher.launch.py` | 2 | 1 | 1 | 0 | ✓ |

**Totais:** 12/12 OK · 45 nodes · 48 args · 9 includes · 100% validação Layer 2.

A demo completa gera:

- 12 JSONs Layer 2 dos launch files reais;
- 58 JSONs Layer 2 dos testes mínimos e de cobertura;
- 70 RDFs Layer 2;
- 12 JSONs de issues estruturais dos exemplos reais;
- 70 JSONs de issues ontológicos;
- 2 JSONs de arquitectura runtime de comunicação;
- 2 RDFs de arquitectura runtime de comunicação;
- 2 JSONs de issues de comunicação.

O exemplo controlado `communication_demo.launch.py` é usado para validar os issues de comunicação. A execução detecta:

```text
1 node isolado
1 publisher sem subscriber
1 subscriber sem publisher
1 topic com múltiplos publishers
1 incompatibilidade de QoS reliability
```

---

## 17. Limitações Conhecidas

Estas limitações são consequência da análise estática:

- **`OpaqueFunction`** — há suporte parcial para padrões simples e loops simbolicamente reconhecíveis; callbacks complexos continuam a exigir execução instrumentada ou anotação manual.
- **`has_resource()`** — é preservado como condição simbólica, mas só pode ser avaliado em runtime.
- **For loops dinâmicos** — loops cujo limite vem de runtime são representados simbolicamente.
- **`os.path.join()` com variáveis** — paths de includes podem ficar parcialmente resolvidos ou marcados como dinâmicos.
- **f-strings com valores dinâmicos** — valores dependentes de variáveis de runtime não são totalmente avaliados.
- **Namespace em Python** — `PushRosNamespace` é registado como acção, mas a herança efectiva de namespace requer análise de escopo mais avançada.
- **Comunicação publish/subscribe** — os launch files normalmente não indicam directamente os publishers/subscribers de cada node. A abordagem atual combina a informação do launch file com ficheiros `node_interfaces/*.communication.yaml`, que representam a interface conhecida dos nodes individuais. Estes ficheiros funcionam como anotações controladas e podem futuramente ser substituídos ou complementados por análise estática de código, documentação dos packages ou descoberta runtime.
- **Qualidade das interfaces dos nodes** — os issues de comunicação dependem da completude dos ficheiros `node_interfaces`. Se faltar anotar um publisher ou subscriber, podem surgir warnings que significam “não encontrado na arquitectura anotada”, não necessariamente erro confirmado no sistema real.
- **Remappings suportados** — os remappings do launch file são aplicados na construção da RuntimeArchitecture, mas casos altamente dinâmicos ou dependentes de substituições runtime podem continuar parcialmente simbólicos.
- **GraphDB** — a análise GraphDB depende de um serviço externo em execução. Por isso, a demo principal não deve depender dele; a integração GraphDB fica numa demo separada.

Quando a análise estática não resolve completamente uma construção dinâmica, o projecto tenta preservar a informação simbolicamente, baixar a confidence ou gerar issues informativos.

---

## 18. Referências

- **Especificação HAROS Layer 2** — documento `haros_layer2.pdf` do professor
- **Especificação HAROS Layer 6** — documento `layer6.pdf` do professor
- **Common Types HAROS** — documento `common.pdf` do professor
- **ROS2 Launch System** — documentação oficial ROS2
- **Lark Parser** — documentação do Lark
- **RDFLib / pySHACL** — bibliotecas usadas para RDF, SPARQL e SHACL

---

## 19. Autores

**Diogo Abreu** — [@Digazz19](https://github.com/Digazz19)  
**Miguel Gramoso** — [@gramosomi](https://github.com/gramosomi)  
**Mariana** — [@wendy077](https://github.com/wendy077)
