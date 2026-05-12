# ProjetoEL — Extracção e Análise de Arquitecturas ROS2

Projeto da UC **Projeto de Engenharia de Linguagens** (Perfil EL, 2025/26) — Universidade do Minho.

Extracção estática de arquitecturas ROS2 a partir de launch files em **XML**, **YAML** e **Python**, produzindo uma representação intermédia **Layer 2** conforme a especificação do **HAROS**. Para além da extracção, o projecto inclui validação estrutural, geração de issues Layer 6, exportação para RDF/Turtle, validação SHACL e análise ontológica através de queries SPARQL.

---

## 🎯 Objetivo

Desenvolver uma pipeline de engenharia de linguagens que, dado um ou vários launch files ROS2, consiga:

1. extrair uma representação intermédia normalizada **Layer 2**;
2. preservar a estrutura simbólica dos launch files, incluindo argumentos, nodes, includes, grupos, namespaces, parâmetros, remappings e condições;
3. validar estruturalmente essa representação;
4. gerar issues arquitecturais em formato inspirado no **HAROS Layer 6**;
5. exportar o modelo para **RDF/Turtle**;
6. validar o grafo com **SHACL**;
7. executar queries **SPARQL** para detectar issues directamente sobre a ontologia.

O output pode ser usado como base para integração com o HAROS ou com ferramentas RDF externas, como GraphDB.

---

## 📁 Estrutura do Projecto

```text
ProjetoEL/
├── main.py                              # Ponto de entrada principal
├── test_layer2.py                       # Testes dos exemplos XML/YAML/Python mínimos e HAROS coverage
├── test_launchfiles.py                  # Teste em lote nos 12 launch files Python reais
├── demo.sh                              # Pipeline completa de demonstração
│
├── models/
│   ├── architectureROS.py               # Modelo legacy
│   ├── layer2.py                        # Modelo Layer 2 HAROS
│   └── layer6.py                        # Issue e ElementRef, inspirados no HAROS Layer 6
│
├── validation/
│   └── layer2_validator.py              # Validador estrutural Layer 2
│
├── issues/
│   ├── catalog.yaml                     # Catálogo externo de issues
│   ├── catalog.py                       # Loader do catálogo
│   ├── detector.py                      # Issues estruturais sobre LaunchDescription
│   ├── ontology_detector.py             # Issues ontológicos via SPARQL
│   └── io.py                            # Escrita de issues em JSON
│
├── ontology/
│   ├── ros_launch.ttl                   # Ontologia base
│   ├── shapes.ttl                       # Shapes SHACL
│   └── queries/                         # Queries SPARQL usadas na análise ontológica
│       ├── node_no_name.rq
│       ├── include_unresolved.rq
│       ├── arg_no_default.rq
│       └── action_without_provenance.rq
│
├── scripts/
│   ├── export_layer2_to_rdf.py          # Exporta um JSON Layer 2 para RDF/Turtle
│   ├── export_all_layer2_to_rdf.py      # Exportação em lote, mantido por compatibilidade
│   ├── run_ontology_issues.py           # Executa issues ontológicos sobre um RDF
│   ├── run_all_ontology_pipeline.py     # Exportação RDF + issues ontológicos para todos os JSONs
│   ├── validate_rdf.py                  # Validação SHACL de um RDF
│   └── validate_all_rdf.py              # Validação SHACL em lote
│
├── parsers/
│   ├── xml/
│   ├── yaml/
│   └── python/
│
├── examples/
│   ├── layer2-minimal/                  # 30 exemplos mínimos
│   ├── layer2-haros-coverage/           # 28 exemplos de cobertura Layer 2
│   └── real-python/                     # 12 launch files ROS2 reais
│
└── output/                              # Artefactos gerados
    ├── *.layer2.json                    # JSONs Layer 2 dos exemplos reais
    ├── layer2-tests/*.layer2.json       # JSONs Layer 2 dos testes
    ├── rdf/*.ttl                        # RDF/Turtle gerado
    └── issues/*.json                    # Issues estruturais e ontológicos
```

---

## 🏗️ Modelo Layer 2

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

## 🚀 Utilização

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
./demo.sh
```

A demo executa compilação, testes, extracção Layer 2, geração de issues estruturais, exportação RDF/Turtle, geração de issues ontológicos por SPARQL, validação SHACL e resumo dos artefactos produzidos.

---

## 📤 Outputs

O projecto gera vários artefactos:

| Artefacto | Caminho | Descrição |
|---|---|---|
| Layer 2 JSON | `output/*.layer2.json` | Modelo simbólico dos launch files reais |
| Layer 2 JSON de testes | `output/layer2-tests/*.layer2.json` | Modelos dos exemplos mínimos e de cobertura |
| Issues estruturais | `output/issues/*.issues.json` | Issues gerados sobre o `LaunchDescription` em memória |
| RDF/Turtle | `output/rdf/*.ttl` | Exportação ontológica do modelo Layer 2 |
| Issues ontológicos | `output/issues/*.ontology.issues.json` | Issues gerados por queries SPARQL sobre RDF |

---

## ✅ Validação Layer 2

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

## ⚠️ Issues Layer 6

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

## 🕸️ Ontologia, RDF, SHACL e SPARQL

O projecto exporta o modelo Layer 2 para RDF/Turtle:

```bash
python3 scripts/export_layer2_to_rdf.py output/robot.launch.layer2.json output/rdf/robot.launch.layer2.ttl
```

O RDF pode ser validado com SHACL:

```bash
python3 scripts/validate_all_rdf.py
```

Também existem issues detectados directamente sobre o grafo RDF através de queries SPARQL:

```bash
python3 scripts/run_ontology_issues.py output/rdf/robot.launch.layer2.ttl
```

Output:

```bash
output/issues/robot.launch.ontology.issues.json
```

Para correr a pipeline ontológica completa sobre todos os JSONs Layer 2:

```bash
python3 scripts/run_all_ontology_pipeline.py output
```

Esta pipeline:

1. encontra todos os ficheiros `*.layer2.json`;
2. gera RDF/Turtle em `output/rdf/`;
3. executa queries SPARQL;
4. converte os resultados em issues Layer 6;
5. guarda os resultados em `output/issues/*.ontology.issues.json`.

---

## 🔬 Funcionalidades Suportadas

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

**Totais:** 12/12 OK · 45 nodes · 48 args · 9 includes · 100% validação Layer 2.

A demo completa gera:

- 12 JSONs Layer 2 dos launch files reais;
- 58 JSONs Layer 2 dos testes mínimos e de cobertura;
- 70 RDFs Layer 2;
- 12 JSONs de issues estruturais;
- 70 JSONs de issues ontológicos.

---

## ⚠️ Limitações Conhecidas

Estas limitações são consequência da análise estática:

- **`OpaqueFunction`** — há suporte parcial para padrões simples e loops simbolicamente reconhecíveis; callbacks complexos continuam a exigir execução instrumentada ou anotação manual.
- **`has_resource()`** — é preservado como condição simbólica, mas só pode ser avaliado em runtime.
- **For loops dinâmicos** — loops cujo limite vem de runtime são representados simbolicamente.
- **`os.path.join()` com variáveis** — paths de includes podem ficar parcialmente resolvidos ou marcados como dinâmicos.
- **f-strings com valores dinâmicos** — valores dependentes de variáveis de runtime não são totalmente avaliados.
- **Namespace em Python** — `PushRosNamespace` é registado como acção, mas a herança efectiva de namespace requer análise de escopo mais avançada.
- **Comunicação publish/subscribe** — launch files nem sempre indicam publishers/subscribers; análises como orphan publisher, subscriber sem publisher ou QoS incompatível exigem informação adicional de código, runtime ou anotações.

Quando a análise estática não resolve completamente uma construção dinâmica, o projecto tenta preservar a informação simbolicamente, baixar a confidence ou gerar issues informativos.

---

## 🔧 Dependências

- Python 3.12+
- Lark
- PyYAML
- rdflib
- pyshacl

Instalação:

```bash
pip install -r requirements.txt
```

---

## 👤 Autores

**Diogo Abreu** — [@Digazz19](https://github.com/Digazz19)  
**Miguel Gramoso** — [@gramosomi](https://github.com/gramosomi)  
**Mariana** — [@wendy077](https://github.com/wendy077)

---

## 📚 Referências

- **Especificação HAROS Layer 2** — documento `haros_layer2.pdf` do professor
- **Especificação HAROS Layer 6** — documento `layer6.pdf` do professor
- **Common Types HAROS** — documento `common.pdf` do professor
- **ROS2 Launch System** — documentação oficial ROS2
- **Lark Parser** — documentação do Lark
- **RDFLib / pySHACL** — bibliotecas usadas para RDF, SPARQL e SHACL
