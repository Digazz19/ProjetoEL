from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

import requests
import yaml

from models.layer6 import Issue, ElementRef
from models.layer2 import SourceRef


PROJECT_ROOT = Path(__file__).resolve().parents[1]


LAYER2_QUERY_KEYS = [
    "node_no_name",
    "include_unresolved",
    "arg_no_default",
    "action_without_provenance",
]

COMMUNICATION_QUERY_KEYS = [
    "isolated_node",
    "publisher_without_subscriber",
    "subscriber_without_publisher",
    "topic_multiple_publishers",
    "qos_reliability_mismatch",
]


AFFECTED_ENTITY_RULES = {
    # Layer 2
    "node_no_name": ("node", ["action_id"]),
    "include_unresolved": ("include", ["action_id"]),
    "arg_no_default": ("arg", ["action_id"]),
    "action_without_provenance": ("action", ["action_id"]),

    # Comunicação runtime
    "isolated_node": ("node", ["runtime_node_id", "node_id"]),
    "publisher_without_subscriber": ("publication", ["publication_id", "topic_id"]),
    "subscriber_without_publisher": ("subscription", ["subscription_id", "topic_id"]),
    "topic_multiple_publishers": ("topic", ["topic_id"]),
    "qos_reliability_mismatch": ("topic", ["topic_id"]),
}


class SafeFormatDict(dict):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_catalog() -> dict:
    catalog_path = PROJECT_ROOT / "issues" / "catalog.yaml"

    with catalog_path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    if "issues" in raw and isinstance(raw["issues"], dict):
        return raw["issues"]

    return raw
    
def format_template(template: str, values: dict) -> str:
    try:
        return template.format_map(SafeFormatDict(values))
    except Exception:
        return template


def binding_value(binding: dict, name: str) -> Optional[str]:
    value = binding.get(name)

    if not isinstance(value, dict):
        return None

    return value.get("value")


def flatten_binding(binding: dict) -> dict:
    result = {}

    for key, value in binding.items():
        if isinstance(value, dict) and "value" in value:
            result[key] = value["value"]

    return result


class GraphDBIssueDetector:
    """
    Executa queries SPARQL no GraphDB e converte os resultados em Issues Layer 6.

    Analisa dois grupos:
    - queries Layer 2: ontology/queries/*.rq
    - queries de comunicação: ontology/queries/communication/*.rq
    """

    def __init__(
        self,
        base_url: str = "http://localhost:7200",
        repo: str = "projetoel",
        catalog: Optional[dict] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.repo = repo
        self.endpoint = f"{self.base_url}/repositories/{self.repo}"
        self.catalog = catalog or load_catalog()

    def detect(self) -> list[Issue]:
        timestamp = utc_now()
        issues: list[Issue] = []
        counters: dict[str, int] = {}

        query_groups = [
            (PROJECT_ROOT / "ontology" / "queries", LAYER2_QUERY_KEYS),
            (PROJECT_ROOT / "ontology" / "queries" / "communication", COMMUNICATION_QUERY_KEYS),
        ]

        for query_dir, query_keys in query_groups:
            for issue_key in query_keys:
                query_path = query_dir / f"{issue_key}.rq"

                if not query_path.exists():
                    continue

                catalog_entry = self.catalog.get(issue_key, {})

                if catalog_entry.get("enabled") is False:
                    continue

                query = query_path.read_text(encoding="utf-8")
                rows = self._run_query(query)

                for row in rows:
                    metadata = flatten_binding(row)
                    metadata["issue_key"] = issue_key
                    metadata["source"] = "graphdb"

                    issue = self._make_issue(
                        issue_key=issue_key,
                        catalog_entry=catalog_entry,
                        metadata=metadata,
                        counters=counters,
                        timestamp=timestamp,
                    )

                    issues.append(issue)

        return issues

    def _run_query(self, query: str) -> list[dict]:
        response = requests.post(
            self.endpoint,
            data={"query": query},
            headers={"Accept": "application/sparql-results+json"},
            timeout=60,
        )

        if response.status_code != 200:
            raise RuntimeError(
                f"Falha na query GraphDB: "
                f"{response.status_code} {response.text[:500]}"
            )

        data = response.json()
        return data.get("results", {}).get("bindings", [])

    def _make_issue(
        self,
        issue_key: str,
        catalog_entry: dict,
        metadata: dict,
        counters: dict[str, int],
        timestamp: str,
    ) -> Issue:
        counters[issue_key] = counters.get(issue_key, 0) + 1

        issue_id = f"graphdb_{issue_key}_{counters[issue_key]:03d}"

        title = catalog_entry.get("title", issue_key)
        recommendation = catalog_entry.get("recommendation")

        if title:
            metadata["title"] = title

        if recommendation:
            metadata["recommendation"] = recommendation

        severity = catalog_entry.get("severity", "info")
        category = catalog_entry.get("category", "architecture")

        description_template = catalog_entry.get(
            "description",
            f"Issue detectado por query GraphDB: {issue_key}",
        )

        description = format_template(description_template, metadata)

        affected_entity = self._affected_entity(issue_key, catalog_entry, metadata)

        location = None
        source_file = metadata.get("source_file")

        if source_file:
            location = SourceRef(file_path=source_file)

        return Issue(
            id=issue_id,
            severity=severity,
            category=category,
            description=description,
            affected_entities=[affected_entity],
            analysis_tool="ProjetoEL-graphdb-analyzer",
            analysis_timestamp=timestamp,
            location=location,
            metadata=metadata,
        )

    def _affected_entity(
        self,
        issue_key: str,
        catalog_entry: dict,
        metadata: dict,
    ) -> ElementRef:
        entity_type, candidate_fields = AFFECTED_ENTITY_RULES.get(
            issue_key,
            (catalog_entry.get("entity_type", "entity"), ["action_id", "entity"]),
        )

        for field in candidate_fields:
            value = metadata.get(field)

            if value:
                return ElementRef(type=entity_type, id=value)

        fallback = metadata.get("entity") or metadata.get("topic_id") or metadata.get("action_id") or "unknown"

        return ElementRef(type=entity_type, id=fallback)