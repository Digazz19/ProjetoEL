#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import quote

from rdflib import Graph, Literal, Namespace, RDF, RDFS, URIRef, XSD


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

ROS = Namespace("http://example.org/ros-launch#")
RES = Namespace("http://example.org/ros-launch/resource/")


def uri(kind: str, raw: str) -> URIRef:
    return URIRef(f"{RES}{kind}/{quote(str(raw), safe='')}")


def add_literal(g: Graph, subject: URIRef, predicate: URIRef, value, datatype=None) -> None:
    if value is None:
        return

    if datatype is not None:
        g.add((subject, predicate, Literal(value, datatype=datatype)))
    else:
        g.add((subject, predicate, Literal(value)))


def add_qos(g: Graph, owner_uri: URIRef, owner_id: str, qos: dict) -> None:
    if not qos:
        return

    qos_uri = uri("qos", f"{owner_id}:qos")

    g.add((qos_uri, RDF.type, ROS.QoSProfile))
    g.add((owner_uri, ROS.hasQoS, qos_uri))

    add_literal(g, qos_uri, ROS.qosReliability, qos.get("reliability"))
    add_literal(g, qos_uri, ROS.qosDurability, qos.get("durability"))
    add_literal(g, qos_uri, ROS.qosHistory, qos.get("history"))

    if qos.get("depth") is not None:
        add_literal(g, qos_uri, ROS.qosDepth, int(qos["depth"]), datatype=XSD.integer)


def architecture_json_to_graph(data: dict) -> Graph:
    g = Graph()

    g.bind("ros", ROS)
    g.bind("res", RES)

    architecture_id = data["id"]
    architecture_uri = uri("architecture", architecture_id)

    g.add((architecture_uri, RDF.type, ROS.RuntimeArchitecture))
    g.add((architecture_uri, RDFS.label, Literal(architecture_id)))

    add_literal(g, architecture_uri, ROS.hasArchitectureId, architecture_id)
    add_literal(g, architecture_uri, ROS.hasConfigurationId, data.get("configuration_id"))
    add_literal(g, architecture_uri, ROS.hasSourceLayer2Path, data.get("source_layer2_path"))
    add_literal(
        g,
        architecture_uri,
        ROS.hasSourceLaunchDescriptionId,
        data.get("source_launch_description_id"),
    )

    # ------------------------------------------------------------------
    # Runtime nodes
    # ------------------------------------------------------------------

    node_uris = {}

    for node_id, node in (data.get("nodes") or {}).items():
        node_uri = uri("runtime-node", node_id)
        node_uris[node_id] = node_uri

        g.add((node_uri, RDF.type, ROS.RuntimeNode))
        g.add((node_uri, RDFS.label, Literal(node.get("runtime_name", node_id))))
        g.add((architecture_uri, ROS.hasRuntimeNode, node_uri))

        add_literal(g, node_uri, ROS.hasRuntimeNodeId, node_id)
        add_literal(g, node_uri, ROS.hasActionId, node.get("action_id"))
        add_literal(g, node_uri, ROS.hasPackage, node.get("package"))
        add_literal(g, node_uri, ROS.hasExecutable, node.get("executable"))
        add_literal(g, node_uri, ROS.hasRuntimeName, node.get("runtime_name"))
        add_literal(g, node_uri, ROS.hasNamespace, node.get("namespace"))
        add_literal(g, node_uri, ROS.hasSourceLayer2Id, node.get("source_layer2_id"))
        add_literal(g, node_uri, ROS.hasNodeImplementationId, node.get("node_implementation_id"))

    # ------------------------------------------------------------------
    # Topics
    # ------------------------------------------------------------------

    topic_uris = {}

    for topic_id, topic in (data.get("topics") or {}).items():
        topic_uri = uri("topic", topic_id)
        topic_uris[topic_id] = topic_uri

        g.add((topic_uri, RDF.type, ROS.Topic))
        g.add((topic_uri, RDFS.label, Literal(topic.get("name", topic_id))))
        g.add((architecture_uri, ROS.hasTopic, topic_uri))

        add_literal(g, topic_uri, ROS.hasTopicId, topic_id)
        add_literal(g, topic_uri, ROS.hasTopicName, topic.get("name"))
        add_literal(g, topic_uri, ROS.hasMessageType, topic.get("msg_type"))

    # ------------------------------------------------------------------
    # Publications
    # ------------------------------------------------------------------

    for publication_id, publication in (data.get("publications") or {}).items():
        publication_uri = uri("publication", publication_id)
        node_uri = node_uris.get(publication.get("node_id"))
        topic_uri = topic_uris.get(publication.get("topic_id"))

        g.add((publication_uri, RDF.type, ROS.Publication))
        g.add((publication_uri, RDFS.label, Literal(publication_id)))
        g.add((architecture_uri, ROS.hasPublication, publication_uri))

        add_literal(g, publication_uri, ROS.hasPublicationId, publication_id)
        add_literal(g, publication_uri, ROS.hasTopicName, publication.get("topic_name"))
        add_literal(g, publication_uri, ROS.hasMessageType, publication.get("msg_type"))     
        add_literal(g, publication_uri, ROS.hasDeclarationId, publication.get("declared_in"))
        add_literal(g, publication_uri, ROS.hasNodeImplementationId, publication.get("node_implementation_id"))
        add_literal(g, publication_uri, ROS.hasSourceLayer2ActionId, publication.get("source_layer2_action_id"))
        add_literal(g, publication_uri, ROS.hasOriginalTopicName, publication.get("original_topic_name"))
        add_literal(g, publication_uri, ROS.hasRemapFrom, publication.get("remap_from"))
        add_literal(g, publication_uri, ROS.hasRemapTo, publication.get("remap_to"))
        add_literal(g, publication_uri, ROS.remapApplied, bool(publication.get("remap_applied")), datatype=XSD.boolean)
 

        if node_uri is not None:
            g.add((publication_uri, ROS.hasPublisher, node_uri))
            g.add((node_uri, ROS.publishes, publication_uri))

        if topic_uri is not None:
            g.add((publication_uri, ROS.onTopic, topic_uri))
            g.add((topic_uri, ROS.hasPublication, publication_uri))

        add_qos(g, publication_uri, publication_id, publication.get("qos") or {})

    # ------------------------------------------------------------------
    # Subscriptions
    # ------------------------------------------------------------------

    for subscription_id, subscription in (data.get("subscriptions") or {}).items():
        subscription_uri = uri("subscription", subscription_id)
        node_uri = node_uris.get(subscription.get("node_id"))
        topic_uri = topic_uris.get(subscription.get("topic_id"))

        g.add((subscription_uri, RDF.type, ROS.Subscription))
        g.add((subscription_uri, RDFS.label, Literal(subscription_id)))
        g.add((architecture_uri, ROS.hasSubscription, subscription_uri))

        add_literal(g, subscription_uri, ROS.hasSubscriptionId, subscription_id)
        add_literal(g, subscription_uri, ROS.hasTopicName, subscription.get("topic_name"))
        add_literal(g, subscription_uri, ROS.hasMessageType, subscription.get("msg_type"))
        add_literal(g, subscription_uri, ROS.hasDeclarationId, subscription.get("declared_in"))
        add_literal(g, subscription_uri, ROS.hasNodeImplementationId, subscription.get("node_implementation_id"))
        add_literal(g, subscription_uri, ROS.hasSourceLayer2ActionId, subscription.get("source_layer2_action_id"))
        add_literal(g, subscription_uri, ROS.hasOriginalTopicName, subscription.get("original_topic_name"))
        add_literal(g, subscription_uri, ROS.hasRemapFrom, subscription.get("remap_from"))
        add_literal(g, subscription_uri, ROS.hasRemapTo, subscription.get("remap_to"))
        add_literal(g, subscription_uri, ROS.remapApplied, bool(subscription.get("remap_applied")), datatype=XSD.boolean)
 

        if node_uri is not None:
            g.add((subscription_uri, ROS.hasSubscriber, node_uri))
            g.add((node_uri, ROS.subscribes, subscription_uri))

        if topic_uri is not None:
            g.add((subscription_uri, ROS.onTopic, topic_uri))
            g.add((topic_uri, ROS.hasSubscription, subscription_uri))

        add_qos(g, subscription_uri, subscription_id, subscription.get("qos") or {})

    return g


def output_path_for(input_path: Path) -> Path:
    base = input_path.name

    if base.endswith(".architecture.json"):
        stem = base[:-len(".architecture.json")]
    else:
        stem = input_path.stem

    return Path("output") / "rdf" / "architecture" / f"{stem}.architecture.ttl"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Exporta RuntimeArchitecture JSON para RDF/Turtle."
    )
    parser.add_argument("architecture_json")
    parser.add_argument(
        "output_ttl",
        nargs="?",
        help="Caminho de output RDF/Turtle. Por omissão: output/rdf/architecture/<nome>.architecture.ttl",
    )

    args = parser.parse_args()

    input_path = Path(args.architecture_json)

    if not input_path.exists():
        print(f"[ERRO] Arquitetura JSON não encontrada: {input_path}")
        return 1

    output_path = Path(args.output_ttl) if args.output_ttl else output_path_for(input_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with input_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    g = architecture_json_to_graph(data)
    g.serialize(destination=str(output_path), format="turtle")

    print(f"[OK] RDF de arquitetura gerado: {output_path}")
    print(f"[OK] triples: {len(g)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())