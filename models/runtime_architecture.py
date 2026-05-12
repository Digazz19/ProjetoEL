from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class QoSProfile:
    reliability: Optional[str] = None
    durability: Optional[str] = None
    history: Optional[str] = None
    depth: Optional[int] = None

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "QoSProfile":
        data = data or {}

        return cls(
            reliability=data.get("reliability"),
            durability=data.get("durability"),
            history=data.get("history"),
            depth=data.get("depth"),
        )

    def to_dict(self) -> dict:
        d = {}

        if self.reliability is not None:
            d["reliability"] = self.reliability
        if self.durability is not None:
            d["durability"] = self.durability
        if self.history is not None:
            d["history"] = self.history
        if self.depth is not None:
            d["depth"] = self.depth

        return d


@dataclass
class RuntimeNode:
    id: str
    action_id: str
    package: Optional[str]
    executable: Optional[str]
    runtime_name: str
    namespace: Optional[str] = None
    source_layer2_id: Optional[str] = None

    def to_dict(self) -> dict:
        d = {
            "id": self.id,
            "action_id": self.action_id,
            "package": self.package,
            "executable": self.executable,
            "runtime_name": self.runtime_name,
        }

        if self.namespace is not None:
            d["namespace"] = self.namespace
        if self.source_layer2_id is not None:
            d["source_layer2_id"] = self.source_layer2_id

        return d


@dataclass
class Topic:
    id: str
    name: str
    msg_type: Optional[str] = None

    def to_dict(self) -> dict:
        d = {
            "id": self.id,
            "name": self.name,
        }

        if self.msg_type is not None:
            d["msg_type"] = self.msg_type

        return d


@dataclass
class Publication:
    id: str
    node_id: str
    topic_id: str
    topic_name: str
    msg_type: Optional[str] = None
    qos: QoSProfile = field(default_factory=QoSProfile)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "node_id": self.node_id,
            "topic_id": self.topic_id,
            "topic_name": self.topic_name,
            "msg_type": self.msg_type,
            "qos": self.qos.to_dict(),
        }


@dataclass
class Subscription:
    id: str
    node_id: str
    topic_id: str
    topic_name: str
    msg_type: Optional[str] = None
    qos: QoSProfile = field(default_factory=QoSProfile)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "node_id": self.node_id,
            "topic_id": self.topic_id,
            "topic_name": self.topic_name,
            "msg_type": self.msg_type,
            "qos": self.qos.to_dict(),
        }


@dataclass
class RuntimeArchitecture:
    id: str
    source_layer2_path: str
    source_launch_description_id: Optional[str]
    configuration_id: str = "default"

    nodes: Dict[str, RuntimeNode] = field(default_factory=dict)
    topics: Dict[str, Topic] = field(default_factory=dict)
    publications: Dict[str, Publication] = field(default_factory=dict)
    subscriptions: Dict[str, Subscription] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "configuration_id": self.configuration_id,
            "source_layer2_path": self.source_layer2_path,
            "source_launch_description_id": self.source_launch_description_id,
            "nodes": {
                node_id: node.to_dict()
                for node_id, node in self.nodes.items()
            },
            "topics": {
                topic_id: topic.to_dict()
                for topic_id, topic in self.topics.items()
            },
            "publications": {
                pub_id: pub.to_dict()
                for pub_id, pub in self.publications.items()
            },
            "subscriptions": {
                sub_id: sub.to_dict()
                for sub_id, sub in self.subscriptions.items()
            },
            "warnings": self.warnings,
        }