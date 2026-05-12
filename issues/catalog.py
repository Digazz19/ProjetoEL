from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

import yaml


@dataclass
class IssueDefinition:
    key: str
    enabled: bool
    severity: str
    category: str
    title: str
    description: str
    recommendation: Optional[str]
    entity_type: str

    def render_description(self, context: Dict[str, Any]) -> str:
        safe_context = {
            key: "" if value is None else value
            for key, value in context.items()
        }

        try:
            return self.description.format(**safe_context)
        except KeyError as e:
            missing = e.args[0]
            return f"{self.description} [missing_context={missing}]"


class IssueCatalog:
    def __init__(self, definitions: Dict[str, IssueDefinition]):
        self.definitions = definitions

    @classmethod
    def load(cls, path: str = "issues/catalog.yaml") -> "IssueCatalog":
        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

        definitions = {}

        for key, data in (raw.get("issues") or {}).items():
            definitions[key] = IssueDefinition(
                key=key,
                enabled=bool(data.get("enabled", True)),
                severity=data["severity"],
                category=data["category"],
                title=data.get("title", key),
                description=data["description"],
                recommendation=data.get("recommendation"),
                entity_type=data.get("entity_type", "unknown"),
            )

        return cls(definitions)

    def get(self, key: str) -> Optional[IssueDefinition]:
        definition = self.definitions.get(key)

        if definition is None:
            return None

        if not definition.enabled:
            return None

        return definition