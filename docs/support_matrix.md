# Matriz de Suporte Layer 2

Esta matriz documenta o subconjunto de ROS 2 launch suportado pelo extrator Layer 2.

## Localização dos testes

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
| `scripts/export_layer2_to_rdf.py` | Converte um ficheiro JSON Layer 2 individual para RDF/Turtle, usando o vocabulário definido em `ontology/ros_launch.ttl`. |
| `scripts/export_all_layer2_to_rdf.py` | Executa a conversão em lote. Percorre todos os ficheiros `.layer2.json` em `output/layer2-tests/` e chama `export_layer2_to_rdf.py` para cada um. |
| `scripts/validate_rdf.py` | Valida um ficheiro RDF/Turtle individual contra as regras SHACL em `ontology/shapes.ttl`, usando `pyshacl`. |
| `scripts/validate_all_rdf.py` | Executa a validação em lote. Percorre todos os ficheiros `.ttl` em `output/rdf/` e chama `validate_rdf.py` para cada um. |

---

## Suporte atual — testes mínimos

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

## Cobertura HAROS Layer 2 adicional

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

## Ontologia RDF/OWL e validação SHACL

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

`scripts/export_layer2_to_rdf.py`
`scripts/export_all_layer2_to_rdf.py`
`scripts/validate_rdf.py`
`scripts/validate_all_rdf.py`

Resultado atual da exportação RDF:

```text
EXPORTADOS: 56
FALHARAM:   0
```

Resultado atual da validação SHACL:

```text
VÁLIDOS:   56
INVÁLIDOS: 0
```

Isto valida o pipeline:

launch file → Layer2 JSON → RDF/Turtle → SHACL

---

## Regras SHACL atuais

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

## Cobertura ainda em aberto

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
| Publishers/subscribers reais           | fora do Layer 2 atual     | Launch files não indicam necessariamente os topics publicados/subscritos pelos nodes.                       |
| Integração real com HAROS              | por fazer                 | O JSON está próximo do Layer 2, mas ainda não foi consumido diretamente pelo HAROS.                         |
| Regras arquiteturais ROS               | por fazer                 | Ainda não há regras sobre topics, publishers, subscribers ou compatibilidade de mensagens.                  |

---

## Interpretação dos resultados

Os resultados atuais indicam que o extrator já produz uma representação Layer 2 consistente para um subconjunto relevante e testado de ROS 2 launch.

A matriz não afirma suporte completo. Ela documenta, com testes reproduzíveis, o que está atualmente suportado, o que está parcialmente suportado e o que continua fora do escopo ou por testar.

Esta distinção é importante porque os exemplos canónicos são controlados e focados em features específicas. Eles servem para validar a cobertura do modelo intermédio antes de avançar para análises mais sofisticadas.

A fase RDF/SHACL mostra que o JSON Layer 2 já pode ser transformado numa representação baseada em conhecimento e validado por regras declarativas.