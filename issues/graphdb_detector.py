from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import requests

from issues.catalog import IssueCatalog
from issues.ontology_detector import DEFAULT_QUERY_KEYS
from models.layer2 import SourceRef
from models.layer6 import ElementRef, Issue


class GraphDBIssueDetector:
    """
    Executa queries SPARQL num repositório GraphDB e converte os resultados
    em Issues Layer 6.

    Reutiliza:
      - ontology/queries/*.rq
      - issues/catalog.yaml
    """

    def __init__(
        self,
        base_url: str = "http://localhost:7200",
        repo: str = "projetoel",
        catalog: Optional[IssueCatalog] = None,
        query_dir: str = "ontology/queries",
        query_keys: Optional[Iterable[str]] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.repo = repo
        self.endpoint = f"{self.base_url}/repositories/{self.repo}"
        self.catalog = catalog or IssueCatalog.load()
        self.query_dir = Path(query_dir)
        self.query_keys = list(query_keys or DEFAULT_QUERY_KEYS)

    def detect(self) -> List[Issue]:
        issues: List[Issue] = []

        for key in self.query_keys:
            definition = self.catalog.get(key)

            if definition is None:
                continue

            query_path = self.query_dir / f"{key}.rq"

            if not query_path.exists():
                raise FileNotFoundError(f"Query SPARQL não encontrada: {query_path}")

            query = query_path.read_text(encoding="utf-8")
            rows = self._run_query(query)

            for idx, context in enumerate(rows, start=1):
                entity_id = (
                    context.get("action_id")
                    or context.get("entity")
                    or f"unknown_{idx}"
                )

                issue_id = f"graphdb_{key}_{idx:03d}"

                issue = self._make_issue(
                    key=key,
                    issue_id=issue_id,
                    entity_id=str(entity_id),
                    context=context,
                )

                if issue:
                    issues.append(issue)

        return issues

    def _run_query(self, query: str) -> List[Dict[str, str]]:
        response = requests.post(
            self.endpoint,
            data={"query": query},
            headers={
                "Accept": "application/sparql-results+json",
            },
            timeout=60,
        )

        if response.status_code != 200:
            raise RuntimeError(
                f"Falha na query GraphDB: {response.status_code} "
                f"{response.text[:500]}"
            )

        payload = response.json()
        bindings = payload.get("results", {}).get("bindings", [])

        rows = []

        for binding in bindings:
            row = {}

            for key, value in binding.items():
                row[key] = value.get("value")

            rows.append(row)

        return rows

    def _make_issue(
        self,
        key: str,
        issue_id: str,
        entity_id: str,
        context: Dict[str, Any],
    ) -> Optional[Issue]:
        definition = self.catalog.get(key)

        if definition is None:
            return None

        metadata = dict(context)
        metadata["issue_key"] = key
        metadata["title"] = definition.title
        metadata["source"] = "graphdb"

        if definition.recommendation:
            metadata["recommendation"] = definition.recommendation

        source_file = context.get("source_file")
        location = SourceRef(file_path=str(source_file)) if source_file else None

        return Issue(
            id=issue_id,
            severity=definition.severity,
            category=definition.category,
            description=definition.render_description(context),
            affected_entities=[
                ElementRef(
                    type=definition.entity_type,
                    id=entity_id,
                )
            ],
            analysis_tool="ProjetoEL-graphdb-analyzer",
            location=location,
            metadata=metadata,
        )