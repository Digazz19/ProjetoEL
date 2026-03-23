# Análise de Configurações ROS — Fase 1

## Contexto

O ROS2 organiza software robótico em **nodes** que comunicam entre si de forma assíncrona através de **tópicos** (padrão publish-subscribe). As configurações de lançamento desses nodes são descritas em **launch files**, que podem estar em formato XML, YAML ou Python.

Este projeto implementa um pipeline que lê esses ficheiros e constrói uma **representação intermédia** da arquitetura do sistema robótico — ou seja, um modelo que reflete o que acontece em runtime, não apenas o que está escrito no ficheiro.

---

## Arquitetura do Pipeline

```
ficheiro.xml / .yaml
       │
       ▼
  Lark Parser + Gramática
       │  (parse tree)
       ▼
  Transformer (XML ou YAML)
       │  (objetos Node, Remapping, Param)
       ▼
  arch.resolve()
       │  (aplica namespaces, constrói grafo)
       ▼
  ArchitectureROS
  ├── nodes[]
  ├── topics{}   ← grafo de comunicação
  ├── args, lets, includes, env, ...
```

### 1. Gramática (`grammar.py`)

Define a sintaxe aceite dos ficheiros de launch em notação EBNF, usando a biblioteca **Lark**. Há uma gramática para XML e outra para YAML. Estas gramáticas não foram alteradas — definem o que se pode escrever num launch file, e isso não mudou.

### 2. Parser (`parser.py`)

Responsável por ler o ficheiro, invocar o Lark com a gramática correspondente, e passar a parse tree ao transformer. Também não foi alterado.

### 3. Transformer (`transformerXML.py` / `transformerYAML.py`)

Percorre a parse tree e constrói os objetos do modelo intermédio (`Node`, `Remapping`, `Param`). No final do método `launch`, chama `arch.resolve()` para resolver namespaces e construir o grafo de tópicos antes de devolver a arquitetura.

### 4. Modelo Intermédio (`architectureROS.py`)

É aqui que reside a lógica principal. Composto por quatro classes:

---

## O Modelo Intermédio em Detalhe

### `Remapping(src, dst)`

Substitui os tuplos anónimos `("from", "to")` que existiam anteriormente. Um objeto tipado tem semântica clara — `remap.src` e `remap.dst` em vez de `remap[0]` e `remap[1]` — e pode ser inspecionado, comparado e impresso de forma legível.

```python
Remapping(src="chatter", dst="robot_chat")
```

### `Param(name, value)`

Representa um parâmetro de configuração de um node.

### `Topic(name)`

A peça mais importante da refatorização. No modelo anterior, os tópicos não existiam como entidade — eram apenas strings perdidas dentro dos remaps. Agora cada tópico é um objeto de primeira classe com listas de `publishers` e `subscribers`, o que permite representar o **grafo de comunicação** da arquitetura.

```python
Topic(
  name="robot1/robot_chat",
  publishers=[talker_node, listener_node],
  subscribers=[]   # preenchido na Fase 2
)
```

### `Node`

Representa um node ROS2 tal como declarado no launch file. Após `resolve()`, passa a ter também:

- `resolved_name` — nome completo com namespace aplicado (ex: `robot1/talker_node`)
- `resolved_remappings` — remaps com nomes de tópicos já resolvidos em runtime

### `ArchitectureROS`

Contentor principal. Para além das listas de nodes, args, lets, includes, env e executables, passa a ter:

- `topics` — dicionário `nome → Topic`, o grafo de comunicação do sistema

---

## Resolução de Nomes em Runtime

Este é o ponto central da Fase 1. No ROS2, os nomes de tópicos existem em duas formas:

- **Relativos** — ex: `chatter`. O nome real em runtime depende do namespace do node.
- **Absolutos** — ex: `/chatter`. Começam com `/` e são independentes de qualquer namespace.

O método `Node.resolve()` implementa esta lógica. Dado um node com `namespace="robot1"` e um remap `chatter → robot_chat`:

```
chatter       →   robot1/chatter        (relativo, prefixado)
/chatter      →   /chatter              (absoluto, não alterado)
robot_chat    →   robot1/robot_chat     (relativo, prefixado)
/global/chat  →   /global/chat          (absoluto, não alterado)
```

Sem esta resolução, dois nodes em namespaces diferentes com o mesmo remap relativo pareceriam ligados ao mesmo tópico, quando na realidade não estão.

### Exemplo concreto

Dado este launch file:

```xml
<node name="talker_node" namespace="robot1" ...>
  <remap from="chatter" to="robot_chat"/>
</node>

<node name="listener_node" namespace="robot1" ...>
  <remap from="chatter" to="robot_chat"/>
</node>
```

Após `resolve()`, o grafo de tópicos contém:

```
Topic("robot1/robot_chat")
  publishers: [talker_node, listener_node]
  subscribers: []
```

Os dois nodes ficam corretamente associados ao **mesmo** tópico porque partilham o mesmo namespace e o mesmo destino de remap.

---

## O que falta — Fase 2

Os `subscribers` estão atualmente vazios em todos os tópicos. Isto é **esperado e correto** nesta fase.

Saber se um node publica ou subscreve num dado tópico requer analisar o **código-fonte** do node (C++ ou Python) — informação que não está presente no launch file. O launch file apenas declara que o node existe, que namespace tem, e como os seus tópicos são remapeados.

A Fase 2 irá:

1. Analisar o código-fonte dos nodes para extrair publishers e subscribers
2. Cruzar essa informação com os remaps resolvidos da Fase 1
3. Preencher as listas `publishers` e `subscribers` de cada `Topic`
4. Definir uma ontologia e regras de consistência sobre o grafo resultante (ex: tópico sem subscribers, tipo de mensagem incompatível)

---

## Como Correr

```bash
# Instalar dependências
pip install lark

# Correr com ficheiro XML
python3 main.py xml examples/example.launch.xml

# Correr com ficheiro YAML
python3 main.py yaml examples/example.launch.yaml
```

---

## Estrutura de Ficheiros

```
projeto/
├── main.py                        # Ponto de entrada
├── models/
│   └── architectureROS.py         # Modelo intermédio (Remapping, Topic, Node, ArchitectureROS)
├── parsers/
│   ├── xml/
│   │   ├── grammar.py             # Gramática XML (Lark EBNF)
│   │   ├── parser.py              # Parser XML
│   │   └── transformerXML.py      # Transformer XML → modelo
│   └── yaml/
│       ├── grammar.py             # Gramática YAML (Lark EBNF)
│       ├── parser.py              # Parser YAML
│       └── transformerYAML.py     # Transformer YAML → modelo
└── examples/
    ├── example.launch.xml
    └── example.launch.yaml
```