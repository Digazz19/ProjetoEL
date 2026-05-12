from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from models.layer2 import SourceRef


@dataclass
class ElementRef:
    """
    Referência leve a outra entidade do metamodelo.
    Conforme HAROS Common Types.
    """
    type: str
    id: str
    role: Optional[str] = None

    def to_dict(self) -> dict:
        d = {
            "type": self.type,
            "id": self.id,
        }
        if self.role:
            d["role"] = self.role
        return d


@dataclass
class Issue:
    """
    Resultado de análise conforme HAROS Layer 6.
    """
    id: str
    severity: str
    category: str
    description: str
    affected_entities: List[ElementRef]

    analysis_tool: str = "ProjetoEL-extractor"
    analysis_timestamp: Optional[str] = None
    execution_configuration_id: Optional[str] = None
    location: Optional[SourceRef] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = {
            "id": self.id,
            "severity": self.severity,
            "category": self.category,
            "description": self.description,
            "affected_entities": [e.to_dict() for e in self.affected_entities],
            "analysis_tool": self.analysis_tool,
            "analysis_timestamp": (
                self.analysis_timestamp
                or datetime.datetime.utcnow().isoformat() + "Z"
            ),
        }

        if self.execution_configuration_id:
            d["execution_configuration_id"] = self.execution_configuration_id

        if self.location:
            d["location"] = self.location.to_dict()

        if self.metadata:
            d["metadata"] = self.metadata

        return d

    def __str__(self) -> str:
        loc = f" [{self.location.file_path}]" if self.location else ""
        return f"[{self.severity.upper()}] {self.id}{loc}: {self.description}"