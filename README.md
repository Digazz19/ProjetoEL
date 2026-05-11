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
├── output/                              # JSONs Layer 2 gerados
```

---

## 🏗️ Modelo Layer 2

Conforme a especificação `haros_layer2.pdf`, o modelo captura um **programa simbólico de launch**:

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
| `NodeAction` | Instanciação simbólica de node |
| `IncludeAction` | Inclusão de outro launch file |
| `GroupAction` | Agrupamento com scope opcional |

### IDs Hash-based Determinísticos

Formato: `la:<file_id>:<hash8>#<ordinal>`

- `la:` — prefixo de launch action
- `<file_id>` — ID do ficheiro de origem
- `<hash8>` — hash MD5 de 8 hex chars sobre o snippet normalizado
- `<ordinal>` — contador para colisões

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
```

Operadores suportados: `or`, `and`, `not`, `eq`, `neq`, `lt`, `gt`, `lte`, `gte`, `truthy`
Acessores: `env_get`, `launch_arg_get`, `var_get`

### Proveniência

Cada acção e o próprio `LaunchDescription` carregam:

```json
{
  "extraction_method": "static_analysis",
  "source_location": {"file_path": "path/to/file.launch.py"},
  "confidence": 1.0
}
```

A confidence reflecte o nível de certeza — `1.0` para literais, `0.9` para condicionais, `0.85` para o LaunchDescription Python (menor porque a análise estática de Python é mais difícil).

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

- `--tree` - imprime a árvore
- `--json` — também imprime o JSON no terminal
- `--json-file` — força guardar JSON (já é guardado por omissão)

### Teste em lote

```bash
python3 test_launchfiles.py                     # pasta default
python3 test_launchfiles.py examples/real-python
```

---

## 📤 Output

**Terminal** — representação intermédia legível com:
- Tabela de argumentos (NOME | DEFAULT | DESCRIÇÃO)
- Acções principais da sequência
- Acções filhas de grupos/namespaces
- Resultado da validação Layer 2

**Ficheiro JSON** — guardado automaticamente em `output/<nome>.layer2.json`:
- Estrutura completa Layer 2 conforme especificação HAROS
- `actions` como map de IDs, `launch_sequence` como lista ordenada
- Todos os campos simbólicos, provenance, conditions

### Exemplo de output terminal

```
  ════════════════════════════════════════════════════════════════════════
  spawn_robot.launch.py  ·  PYTHON  ·  14 acções  ·  seq=14
  ════════════════════════════════════════════════════════════════════════

  ARGUMENTOS
  ┌────────────────┬────────────────────────────────┬──────────────────────┐
  │ NOME           │ DEFAULT                        │ DESCRIÇÃO            │
  ├────────────────┼────────────────────────────────┼──────────────────────┤
  │ world          │ home.sdf                       │ Name of the Gazebo … │
  │ model          │ mogi_bot.urdf                  │ Name of the URDF de… │
  │ x              │ 2.5                            │ x coordinate of spa… │
  │ use_sim_time   │ True                           │ Flag to enable use_… │
  └────────────────┴────────────────────────────────┴──────────────────────┘

  ACÇÕES PRINCIPAIS
  ────────────────────────────────────────────────────────────────────────
  INCLUDE   world.launch.py

  NODE      ros_gz_sim / create
            param    use_sim_time = $(arg use_sim_time)
            args     -name mogi_bot -topic robot_description -x $(arg x) ...

  NODE      robot_state_publisher / robot_state_publisher   [robot_state_publisher]
            remap    /tf  →  tf
            remap    /tf_static  →  tf_static
            param    use_sim_time = $(arg use_sim_time)
```

---

## ✅ Validação Layer 2

O validador (`Layer2Validator`) verifica 9 regras da especificação:

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

### Parsing — XML
- ✅ `<node>`, `<arg>`, `<include>`, `<group>`, `<let>`, `<set_env>`
- ✅ `<executable>`, `<param>`, `<remap>`, `<env>`
- ✅ Atributos `if` e `unless` (condições)
- ✅ Substituições `$(var ...)`, `$(env ...)`, `$(find-pkg-share ...)`

### Parsing — YAML
- ✅ Estrutura YAML launch ROS2 (`launch:` → elementos)
- ✅ `node`, `arg`, `include`, `group`, `let`, `set_env`
- ✅ `executable`, `param`, `remap`, `env`
- ✅ Indentação via `YamlIndenter`

### Parsing — Python
- ✅ `Node`, `DeclareLaunchArgument`, `IncludeLaunchDescription`
- ✅ `SetEnvironmentVariable`, `ExecuteProcess`
- ✅ `PushRosNamespace` → `PushNamespaceAction`
- ✅ `GroupAction` com preservação de hierarquia (children)
- ✅ `ComposableNode`, `ComposableNodeContainer`, `LoadComposableNodes`
- ✅ `LaunchConfiguration` → argument_reference
- ✅ `os.environ` → environment_variable
- ✅ `list.append()` para construção incremental
- ✅ Condições `if/elif/else` com IR
- ✅ f-strings, subscripts, tuple unpacking
- ✅ `LaunchDescription` simples e qualificado (`launch.LaunchDescription`)
- ✅ Variáveis não resolvidas mantidas como referências pendentes

### Resolução semântica
- ✅ Variáveis resolvidas em tempo de transformação
- ✅ Flatten correcto de listas aninhadas
- ✅ Concatenação `declared_args + [outros]`
- ✅ Filtragem de items não-acção

---

## 📊 Resultados de Teste

Testado em **12 launch files Python reais** (pasta `examples/real-python/`):

| Ficheiro | Acções | Nodes | Args | Includes | Validação |
|---|--:|--:|--:|--:|:-:|
| `bringup_launch.py` | 25 | 1 | 17 | 5 | ✓ |
| `camera.launch.py` | 7 | 2 | 5 | 0 | ✓ |
| `multi_nodes_no_opaque.launch.py` | 1 | 0 | 1 | 0 | ✓ |
| `navigation_launch.py` | 39 | 24 | 12 | 0 | ✓ |
| `on_shutdown_example.launch.py` | 2 | 1 | 0 | 0 | ✓ |
| `opaque_multi_nodes.launch.py` | 1 | 0 | 1 | 0 | ✓ |
| `opaque_multi_nodes_inplace.launch.py` | 0 | 0 | 0 | 0 | ✓ |
| `robot.launch.py` | 8 | 1 | 4 | 2 | ✓ |
| `rviz2.launch.py` | 1 | 1 | 0 | 0 | ✓ |
| `spawn_robot.launch.py` | 14 | 7 | 6 | 1 | ✓ |
| `topic_params.launch.py` | 3 | 2 | 0 | 1 | ✓ |
| `turtlebot3_state_publisher.launch.py` | 2 | 1 | 1 | 0 | ✓ |

**Totais:** 12/12 OK · 40 nodes · 47 args · 9 includes · 100% validação Layer 2.

---

## ⚠️ Limitações Conhecidas

Estas limitações são fundamentais da análise estática — são resolvíveis apenas em runtime:

- **`OpaqueFunction`** com callbacks a funções auxiliares — nodes criados dinamicamente não são extraíveis (ex: `opaque_multi_nodes.launch.py`)
- **`has_resource()`** — condições avaliadas apenas em runtime
- **For loops dinâmicos** — `for i in range(N)` com `N` vindo de runtime
- **`os.path.join()` com variáveis** — paths de includes ficam não resolvidos
- **f-strings com valores dinâmicos** — algumas aspas ficam mal interpretadas
- **Namespace em Python** — `PushRosNamespace` é registado como acção mas os filhos não herdam explicitamente o namespace (análise de fluxo seria necessária)

Todas as limitações estão documentadas e validadas honestamente — o output correcto para casos impossíveis é `0 acções`.

---

## 🔧 Dependências

- **Python 3.12+**
- **Lark** (`pip install lark`)

---

## 👤 Autores

**Diogo Abreu** — [@Digazz19](https://github.com/Digazz19)
**Miguel Gramoso** — [@gramosomi](https://github.com/gramosomi)
**Mariana** — [@wendy077](https://github.com/wendy077)

---

## 📚 Referências

- **Especificação HAROS Layer 2** — documento `haros_layer2.pdf` do professor
- **ROS2 Launch System** — [docs.ros.org](https://docs.ros.org/en/humble/Tutorials/Intermediate/Launch/)
- **Lark Parser** — [github.com/lark-parser/lark](https://github.com/lark-parser/lark)