class Remapping:
    """Representa um remap de tópico/serviço definido num launch file.
    
    src: nome original (hardcoded no node ou relativo)
    dst: nome de destino após remap
    """

    def __init__(self, src, dst):
        self.src = src
        self.dst = dst

    def __repr__(self):
        return f"Remapping({self.src} -> {self.dst})"


class Topic:
    """Representa um tópico ROS2 com o nome já resolvido (pós-namespace e pós-remap).
    
    É uma entidade de primeira classe no grafo de comunicação:
    guarda quais nodes publicam e subscrevem neste tópico.
    """

    def __init__(self, name):
        self.name = name          # nome final em runtime
        self.publishers = []      # lista de Node que publicam
        self.subscribers = []     # lista de Node que subscrevem

    def __repr__(self):
        pub_names = [n.name for n in self.publishers]
        sub_names = [n.name for n in self.subscribers]
        return f"Topic({self.name}, publishers={pub_names}, subscribers={sub_names})"


class Param:

    def __init__(self, name, value):
        self.name = name
        self.value = value

    def __repr__(self):
        return f"{self.name}={self.value}"


class Node:
    """Representa um node ROS2 tal como declarado no launch file.
    
    O nome e os remaps ainda não estão resolvidos — isso é feito por
    ArchitectureROS.resolve() após o parsing estar completo.
    """

    def __init__(self, name, package, exec,
                 namespace=None,
                 remappings=None,
                 params=None,
                 args=None):

        self.name = name
        self.package = package
        self.exec = exec
        self.namespace = namespace
        self.remappings = remappings or []   # lista de Remapping
        self.params = params or []
        self.args = args

        # Preenchido por ArchitectureROS.resolve()
        self.resolved_name = None       # nome completo: /namespace/name
        self.resolved_remappings = []   # lista de Remapping com nomes resolvidos

    def _apply_namespace(self, ns, name):
        """Aplica um namespace a um nome de tópico relativo.
        
        Nomes que já começam com '/' são absolutos e não são afetados.
        Um namespace vazio ou None é tratado como '/'.
        """
        if name is None:
            return None
        if name.startswith("/"):
            return name   # nome absoluto — não alterar
        ns = (ns or "").rstrip("/")
        if not ns:
            return f"/{name}"
        return f"{ns}/{name}"

    def resolve(self, global_namespace=None):
        """Resolve o nome do node e os remaps aplicando o namespace.
        
        Ordem de precedência (igual ao ROS2):
          1. namespace do próprio node (self.namespace)
          2. namespace herdado do grupo / global (global_namespace)
        """
        ns = self.namespace or global_namespace or ""

        # Nome resolvido do node
        if self.name:
            self.resolved_name = self._apply_namespace(ns, self.name)
        else:
            self.resolved_name = None

        # Remaps resolvidos: aplica namespace ao src e ao dst
        self.resolved_remappings = [
            Remapping(
                src=self._apply_namespace(ns, r.src),
                dst=self._apply_namespace(ns, r.dst)
            )
            for r in self.remappings
        ]

    def __repr__(self):
        return (
            f"\nNode(\n"
            f"  name={self.name},\n"
            f"  resolved_name={self.resolved_name},\n"
            f"  pkg={self.package},\n"
            f"  exec={self.exec},\n"
            f"  namespace={self.namespace},\n"
            f"  remaps={self.remappings},\n"
            f"  resolved_remaps={self.resolved_remappings},\n"
            f"  params={self.params},\n"
            f"  args={self.args}\n"
            f")"
        )


class ArchitectureROS:
    """Representação intermédia de uma arquitectura ROS2 extraída de launch files.
    
    Após parsing, chamar resolve() para:
      - resolver nomes de nodes e remaps (aplicando namespaces)
      - construir o grafo de tópicos (topics)
    
    NOTA: o grafo de tópicos (publishers/subscribers) só fica completo
    quando o código-fonte dos nodes for analisado (Fase 2). Aqui guardamos
    apenas a informação estrutural extraída dos launch files.
    """

    def __init__(self):
        self.nodes = []
        self.topics = {}        # dict: nome_resolvido -> Topic
        self.args = {}
        self.lets = {}
        self.includes = []
        self.executables = []
        self.env = {}
        self.unset_env = []

    def add_node(self, node):
        self.nodes.append(node)

    def _get_or_create_topic(self, name):
        """Devolve o Topic existente ou cria um novo."""
        if name not in self.topics:
            self.topics[name] = Topic(name)
        return self.topics[name]

    def resolve(self, global_namespace=None):
        """Resolve todos os nodes e constrói o grafo de tópicos.
        
        Deve ser chamado depois de todos os nodes terem sido adicionados.
        global_namespace: namespace raiz (ex: '/robot1'), opcional.
        """
        for node in self.nodes:
            node.resolve(global_namespace=global_namespace)

            # Para cada remap resolvido, registar a ligação no grafo de tópicos.
            # src = tópico original (como o node o publica/subscreve internamente)
            # dst = tópico final em runtime (após remap)
            # Nesta fase não sabemos se o node publica ou subscreve — isso vem
            # da análise do código-fonte (Fase 2). Por agora, criamos o Topic
            # e associamos o node como "participante" via remaps.
            for remap in node.resolved_remappings:
                if remap.dst:
                    topic = self._get_or_create_topic(remap.dst)
                    # Guardamos o node como potencial participante
                    # (publisher ou subscriber será determinado na Fase 2)
                    if node not in topic.publishers and node not in topic.subscribers:
                        topic.publishers.append(node)  # placeholder até Fase 2

    def print_summary(self):
        print(f"\n=== ARQUITETURA EXTRAÍDA ===\n")

        if self.nodes:
            for i, node in enumerate(self.nodes, 1):
                print(f"[NODE {i}] {node.resolved_name or node.name}")
                print(f"  pkg={node.package}, exec={node.exec}")
                if node.remappings:
                    print(f"  remaps:")
                    for r in node.resolved_remappings:
                        print(f"    {r}")
                if node.params:
                    print(f"  params={node.params}")
                print()
        else:
            print("Sem nodes extraídos.\n")

        if self.topics:
            print("=== GRAFO DE TÓPICOS ===\n")
            for name, topic in self.topics.items():
                print(f"  {topic}")

        print(f"\nARGS: {self.args}")
        print(f"LETS: {self.lets}")
        print(f"INCLUDES: {self.includes}")
        print(f"ENV: {self.env}")
        print(f"UNSET_ENV: {self.unset_env}")
        print(f"EXECUTABLES: {self.executables}")