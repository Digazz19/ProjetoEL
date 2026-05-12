from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from rdflib import Graph

from issues.catalog import IssueCatalog
from models.layer2 import SourceRef
from models.layer6 import ElementRef, Issue


DEFAULT_QUERY_KEYS = [
    "node_no_name",
    "include_unresolved",
    "arg_no_default",
    "action_without_provenance",
]


class OntologyIssueDetector:
    """
    Executa queries SPARQL sobre um grafo RDF e converte os resultados
    para Issues Layer 6.

    As queries vivem em ontology/queries/*.rq.
    As definições dos issues vivem em issues/catalog.yaml.
    """

    def __init__(
        self,
        catalog: Optional[IssueCatalog] = None,
        query_dir: str = "ontology/queries",
        query_keys: Optional[Iterable[str]] = None,
    ):
        self.catalog = catalog or IssueCatalog.load()
        self.query_dir = Path(query_dir)
        self.query_keys = list(query_keys or DEFAULT_QUERY_KEYS)

    def detect_from_file(self, rdf_path: str) -> List[Issue]:
        graph = Graph()
        graph.parse(rdf_path, format=self._guess_format(rdf_path))
        return self.detect(graph)

    def detect(self, graph: Graph) -> List[Issue]:
        issues: List[Issue] = []

        for key in self.query_keys:
            definition = self.catalog.get(key)

            if definition is None:
                continue

            query_path = self.query_dir / f"{key}.rq"

            if not query_path.exists():
                raise FileNotFoundError(f"Query SPARQL não encontrada: {query_path}")

            query = query_path.read_text(encoding="utf-8")
            results = graph.query(query)

            for idx, row in enumerate(results, start=1):
                context = self._row_to_context(row)

                entity_id = (
                    context.get("action_id")
                    or context.get("entity")
                    or f"unknown_{idx}"
                )

                issue_id = f"ontology_{key}_{idx:03d}"

                issue = self._make_issue(
                    key=key,
                    issue_id=issue_id,
                    entity_id=str(entity_id),
                    context=context,
                )

                if issue:
                    issues.append(issue)

        return issues

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
        metadata["source"] = "ontology"

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
            analysis_tool="ProjetoEL-ontology-analyzer",
            location=location,
            metadata=metadata,
        )

    def _row_to_context(self, row) -> Dict[str, Any]:
        context: Dict[str, Any] = {}

        labels = row.labels

        for label in labels:
            value = row[label]
            context[str(label)] = str(value)

        return context

    def _guess_format(self, rdf_path: str) -> str:
        path = rdf_path.lower()

        if path.endswith(".ttl"):
            return "turtle"

        if path.endswith(".rdf") or path.endswith(".xml"):
            return "xml"

        if path.endswith(".nt"):
            return "nt"

        if path.endswith(".jsonld"):
            return "json-ld"

        return "turtle"