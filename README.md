# ProjetoEL — Extracção de Arquitecturas ROS2 (Layer 2 HAROS)

Projeto da UC **Projeto de Engenharia de Linguagens** (Perfil EL, 2025/26) — Universidade do Minho.

Extracção estática de arquitecturas ROS2 a partir de launch files em **XML**, **YAML** e **Python**, produzindo uma representação intermédia **Layer 2** conforme a especificação do **HAROS**.

---

## 🎯 Objetivo

Desenvolver um sistema de análise estática que, dado um launch file ROS2 em qualquer dos três formatos suportados, produz um modelo intermédio normalizado (Layer 2) que representa a arquitectura do sistema — nodes, argumentos, includes, grupos, namespaces, remappings, parameters — preservando a estrutura hierárquica e semântica simbólica.

O output pode ser consumido posteriormente pelo HAROS para análises arquitecturais adicionais.

---

## 📁 Estrutura do Projecto

```
ProjetoEL/
├── main.py                              # Ponto de entrada principal
├── test_launchfiles.py                  # Teste em lote nos 12 ficheiros
│
├── models/
│   ├── architectureROS.py              # Modelo legacy (Fase 1)
│   └── layer2.py                       # Modelo Layer 2 HAROS (Fase 2)
│
├── parsers/
│   ├── xml/
│   │   ├── grammar.py                  # Gramática Lark XML
│   │   ├── parser.py                   # Parser XML
│   │   └── transformerXML.py           # Transformer → Layer 2
│   ├── yaml/
│   │   ├── grammar.py                  # Gramática Lark YAML
│   │   ├── parser.py                   # Parser YAML (com YamlIndenter)
│   │   └── transformerYAML.py          # Transformer → Layer 2
│   └── python/
│       ├── grammar_python.lark         # Gramática Lark Python
│       ├── parser.py                   # Parser Python (com PythonIndenter)
│       └── transformerPython.py        # Transformer → Layer 2
│
├── examples/
│   ├── example.launch.xml
│   ├── example.launch.yaml
│   ├── example.launch.py
│   └── real-python/                    # 12 launch files ROS2 reais
│
├── output/                             # JSONs Layer 2 gerados automaticamente
│
└── docs/
    ├── docs/
    ├── haros_layer2.pdf            # Especificação Layer 2 — estrutura do modelo intermédio
    ├── common.pdf                  # Tipos comuns HAROS (SourceRef, ElementProvenance, QoSProfile)
    ├── layer6.pdf                  # Especificação Layer 6 — análise de resultados (Issues, Metrics)
    └── README.md                   # Documentação técnica detalhada da estratégia de extracção
```

---

## 🏗️ Modelo Layer 2

Conforme a especificação `haros_layer2.pdf` e `common.pdf`, o modelo captura um **programa simbólico de launch**:

### Estrutura principal

```python
LaunchDescription:
    id: string                        # "launch_desc_<file_id>"
    launch_file_id: string            # ID do ficheiro Layer 0
    format: "xml" | "yaml" | "python"
    actions: Dict[str, LaunchAction]  # Mapa de acções por ID
    launch_sequence: List[str]        # Ordem de execução (IDs)
    provenance: ElementProvenance
```

### Tipos de Acções

| Acção | Descrição |
|---|---|
| `DeclareArgumentAction` | Declaração de argumento launch |
| `SetParameterAction` | Definição de parâmetro no escopo |
| `PushNamespaceAction` | Introdução de namespace |
| `NodeAction` | Instanciação simbólica de node (inclui ComposableNode) |
| `IncludeAction` | Inclusão de outro launch file |
| `GroupAction` | Agrupamento com scope opcional e hierarquia preservada |

### IDs Hash-based Determinísticos

Formato: `la:<file_id>:<hash8>#<ordinal>`

**Propriedades:**
- ✅ Estáveis a formatting, comentários e ordem de kwargs
- ✅ Determinísticos (mesma fonte → mesmo ID)
- ✅ **Consistentes entre formatos** — o mesmo node em XML e YAML gera o mesmo hash

### LaunchSubstitution (União Discriminada)

Valores simbólicos que permanecem não avaliados até runtime:

```json
{"type": "literal", "value": 30}
{"type": "argument_reference", "argument_name": "use_sim"}
{"type": "environment_variable", "variable_name": "ROS_DISTRO"}
{"type": "file_path", "package": "pkg", "relative_path": "config.yaml"}
{"type": "expression", "expression": [...]}
```

### Condições IR

Expressões simbólicas em forma de árvore:

```python
# Fonte Python:
if ROS_DISTRO == 'humble':
    ...
# IR extraído:
[["eq", ["env_get", "ROS_DISTRO"], "humble"]]

# IfCondition(LaunchConfiguration('use_sim'))
[["eq", ["launch_arg_get", "use_sim"], "true"]]

# For loop simbólico:
[["truthy", ["var_get", "for i in range($(arg num_node_pairs))"]]]
```

Operadores: `or`, `and`, `not`, `eq`, `neq`, `lt`, `gt`, `lte`, `gte`, `truthy`
Acessores: `env_get`, `launch_arg_get`, `var_get`

### Proveniência (conforme `common.pdf`)

Cada acção e o próprio `LaunchDescription` carregam:

```json
{
  "extraction_method": "static_analysis",
  "confidence": 1.0,
  "source_location": {"file_path": "path/to/file.launch.py"},
  "extractor_version": "ProjetoEL-2025",
  "extraction_context": {"parser": "lark", "format": "py"}
}
```

Escala de `confidence`: `1.0` (literal) → `0.9` (condicional) → `0.85` (LaunchDescription Python) → `0.8` (arg órfão)

---

## 🚀 Utilização

### Processar um ficheiro único

```bash
python3 main.py python examples/real-python/spawn_robot.launch.py
python3 main.py xml    examples/example.launch.xml
python3 main.py yaml   examples/example.launch.yaml
python3 main.py auto   examples/example.launch.xml  # detecta o formato
```

### Processar uma pasta inteira

```bash
python3 main.py python examples/real-python
```

### Opções

| Opção | Descrição |
|---|---|
| `--no-tree` | Omite a parse tree (recomendado para uso normal) |
| `--tree` | Mostra a parse tree Lark no terminal |
| `--json` | Imprime o JSON Layer 2 completo no terminal (para além do summary) |
| `--json-file` | Força guardar o JSON em ficheiro (já é guardado por omissão) |

> O JSON é **sempre** guardado em `output/<nome>.layer2.json` independentemente das opções.

### Teste em lote

```bash
python3 test_launchfiles.py
python3 test_launchfiles.py examples/real-python
```

O JSON Layer 2 é guardado **automaticamente** em `output/<nome>.layer2.json` em todos os modos.

---

## 📤 Output

**Terminal** — representação intermédia legível:

```
  ════════════════════════════════════════════════════════════════════════
  spawn_robot.launch.py  ·  PYTHON  ·  14 acções  ·  seq=14
  ════════════════════════════════════════════════════════════════════════

  ARGUMENTOS
  ┌────────────────┬─────────────────┬─────────────────────────────────────┐
  │ NOME           │ DEFAULT         │ DESCRIÇÃO                           │
  ├────────────────┼─────────────────┼─────────────────────────────────────┤
  │ world          │ home.sdf        │ Name of the Gazebo world file       │
  │ use_sim_time   │ True            │ Flag to enable use_sim_time         │
  └────────────────┴─────────────────┴─────────────────────────────────────┘

  ACÇÕES PRINCIPAIS
  ──────────────────────────────────────────────────────────────────────────
  INCLUDE   world.launch.py

  NODE      ros_gz_sim / create
            param    use_sim_time = $(arg use_sim_time)
            args     -x $(arg x) -y $(arg y) -z 0.5 -Y $(arg yaw)

  NODE      robot_state_publisher / robot_state_publisher   [robot_state_publisher]
            remap    /tf  →  tf
            param    use_sim_time = $(arg use_sim_time)

  [JSON guardado em: output/spawn_robot.launch.layer2.json]
  [VALIDAÇÃO ✓ sem erros]
```

---

## ✅ Validação Layer 2

O validador (`Layer2Validator`) verifica 9 regras:

1. **actions_map_consistency** — chaves do mapa correspondem aos IDs
2. **sequence_validity** — IDs na sequência existem no mapa
3. **reachability** — acções são alcançáveis
4. **no_orphans** — sem acções órfãs
5. **id_format** — IDs seguem `la:<file>:<hash>#<ordinal>`
6. **no_cycles** — árvore acíclica
7. **scope_actions_only** — só group/push_namespace/include têm children
8. **node_required_fields** — NodeAction tem package e executable
9. **include_required_fields** — IncludeAction tem included_launch_id

---

## 🔬 Funcionalidades Suportadas

### XML
- ✅ `<node>`, `<arg>`, `<include>`, `<group>`, `<let>`, `<set_env>`, `<push-ros-namespace>`
- ✅ `<param>`, `<remap>`, `<env>`, `<executable>`
- ✅ Atributos `if` e `unless` com condições IR
- ✅ Substituições `$(var ...)`, `$(env ...)`, `$(find-pkg-share ...)`

### YAML
- ✅ Estrutura YAML launch ROS2 com `YamlIndenter`
- ✅ `node`, `arg`, `include`, `group`, `let`, `set_env`
- ✅ `param`, `remap`, `env`

### Python
- ✅ `Node`, `DeclareLaunchArgument`, `IncludeLaunchDescription`
- ✅ `SetEnvironmentVariable`, `ExecuteProcess`, `SetParameter`
- ✅ `PushRosNamespace` → `PushNamespaceAction`
- ✅ `GroupAction` com hierarquia preservada (`children` IDs)
- ✅ `ComposableNode`, `ComposableNodeContainer`, `LoadComposableNodes`
- ✅ `IfCondition`, `UnlessCondition` → condições IR
- ✅ `OpaqueFunction` — análise de funções auxiliares com `for` loops simbólicos
- ✅ `LaunchConfiguration` → `argument_reference`
- ✅ `os.environ` → `environment_variable`
- ✅ `list.append()` para construção incremental de listas
- ✅ `if/elif/else` com extracção de condições IR
- ✅ `for i in range(N)` → condição simbólica `for i in range($(arg N))`
- ✅ `LaunchDescription` simples e qualificado (`launch.LaunchDescription`)
- ✅ Args declarados mas não adicionados ao `ld` (args órfãos com `confidence=0.8`)
- ✅ Concatenação `declared_args + [outros]`

---

## 📊 Resultados de Teste

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

**12/12 OK · 100% validação Layer 2**

---

## ⚠️ Limitações Conhecidas

Limitações fundamentais da análise estática — resolvíveis apenas em runtime:

- **`OpaqueFunction` com callbacks inacessíveis** — quando a função auxiliar usa lógica impossível de analisar (ex: `N_lc.perform(context)`), os nodes são extraídos com condição simbólica `for i in range($(arg N))`
- **`has_resource()`** — condição de runtime; o node é extraído com condição simbólica
- **`os.path.join(variavel, ...)`** — paths de includes com variáveis não resolvidas ficam com ID parcial
- **f-strings com variáveis de loop** — `f"ns{i}"` guardado como `"ns{i}"` literal
- **Classes externas** — `LaunchConfigAsBool` (nav2_common) guardada como string

---

## 🔧 Dependências

```bash
pip install lark
```

- **Python 3.12+**
- **Lark** — parser PEG/LALR

---

## 📚 Documentação

- `docs/README.md` — estratégia detalhada de extracção, casos complexos e limitações

---

## 👤 Autores

**Diogo Abreu** — [@Digazz19](https://github.com/Digazz19)
**Miguel Gramoso** — [@gramosomi](https://github.com/gramosomi)
**Mariana** — [@wendy077](https://github.com/wendy077)

---

## 📚 Referências

- **Especificação HAROS Layer 2** — `haros_layer2.pdf`
- **HAROS Common Types** — `common.pdf`
- **ROS2 Launch System** — [docs.ros.org](https://docs.ros.org/en/humble/Tutorials/Intermediate/Launch/)
- **Lark Parser** — [github.com/lark-parser/lark](https://github.com/lark-parser/lark)