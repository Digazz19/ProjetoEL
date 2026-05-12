from __future__ import annotations

from typing import Any, Dict, List, Optional

from models.layer2 import (
    DeclareArgumentAction,
    IncludeAction,
    LaunchDescription,
    NodeAction,
    PushNamespaceAction,
    SubstitutionType,
)

from models.layer6 import Issue, ElementRef
from issues.catalog import IssueCatalog


class IssueDetector:
    """
    Analisa um LaunchDescription e produz Issues Layer 6.

    As definições dos issues vêm de issues/catalog.yaml.
    O código apenas detecta as condições estruturais.
    """

    def __init__(self, catalog: Optional[IssueCatalog] = None):
        self.catalog = catalog or IssueCatalog.load()

    def detect(self, ld: LaunchDescription) -> List[Issue]:
        issues = []
        issues.extend(self._check_nodes(ld))
        issues.extend(self._check_includes(ld))
        issues.extend(self._check_args(ld))
        issues.extend(self._check_namespace(ld))
        return issues

    def _make_issue(
        self,
        key: str,
        issue_id: str,
        entity_id: str,
        context: Dict[str, Any],
        location=None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Issue]:
        definition = self.catalog.get(key)

        if definition is None:
            return None

        issue_metadata = dict(metadata or {})

        if definition.recommendation:
            issue_metadata["recommendation"] = definition.recommendation

        issue_metadata["issue_key"] = key
        issue_metadata["title"] = definition.title

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
            location=location,
            metadata=issue_metadata,
        )

    def _source_location(self, action):
        return action.provenance.source_location if action.provenance else None

    def _node_context(self, action: NodeAction) -> Dict[str, Any]:
        return {
            "package": action.package.display() if action.package else None,
            "executable": action.executable.display() if action.executable else None,
        }

    # -----------------------------------------------------------------------
    # Nodes
    # -----------------------------------------------------------------------

    def _check_nodes(self, ld: LaunchDescription) -> List[Issue]:
        issues = []
        counter = [0]

        def _issue_id():
            counter[0] += 1
            return f"issue_{ld.launch_file_id}_{counter[0]:03d}"

        for aid, action in ld.actions.items():
            if not isinstance(action, NodeAction):
                continue

            node_context = self._node_context(action)

            if not action.name:
                issue = self._make_issue(
                    key="node_no_name",
                    issue_id=_issue_id(),
                    entity_id=aid,
                    context=node_context,
                    location=self._source_location(action),
                    metadata=node_context,
                )

                if issue:
                    issues.append(issue)

            for cond in action.conditions:
                cond_str = str(cond)

                if "has_resource" in cond_str:
                    context = {
                        **node_context,
                        "condition": cond_str,
                    }

                    issue = self._make_issue(
                        key="node_runtime_condition",
                        issue_id=_issue_id(),
                        entity_id=aid,
                        context=context,
                        location=self._source_location(action),
                        metadata=context,
                    )

                    if issue:
                        issues.append(issue)

                elif "for" in cond_str and "range" in cond_str:
                    context = {
                        **node_context,
                        "condition": cond_str,
                    }

                    issue = self._make_issue(
                        key="opaque_symbolic_node",
                        issue_id=_issue_id(),
                        entity_id=aid,
                        context=context,
                        location=self._source_location(action),
                        metadata=context,
                    )

                    if issue:
                        issues.append(issue)

        return issues

    # -----------------------------------------------------------------------
    # Includes
    # -----------------------------------------------------------------------

    def _check_includes(self, ld: LaunchDescription) -> List[Issue]:
        issues = []
        counter = [0]

        def _issue_id():
            counter[0] += 1
            return f"issue_{ld.launch_file_id}_inc_{counter[0]:03d}"

        for aid, action in ld.actions.items():
            if not isinstance(action, IncludeAction):
                continue

            inc_id = action.included_launch_id

            if (
                "os_path_join" in inc_id
                or "type____var" in inc_id
                or "type____launch" in inc_id
            ):
                context = {
                    "included_launch_id": inc_id,
                }

                issue = self._make_issue(
                    key="include_unresolved",
                    issue_id=_issue_id(),
                    entity_id=aid,
                    context=context,
                    location=self._source_location(action),
                    metadata=context,
                )

                if issue:
                    issues.append(issue)

            if inc_id == ld.id or inc_id == f"launch_desc_{ld.launch_file_id}":
                context = {
                    "included_launch_id": inc_id,
                    "launch_description_id": ld.id,
                }

                issue = self._make_issue(
                    key="include_self",
                    issue_id=_issue_id(),
                    entity_id=aid,
                    context=context,
                    location=self._source_location(action),
                    metadata=context,
                )

                if issue:
                    issues.append(issue)

        return issues

    # -----------------------------------------------------------------------
    # Args
    # -----------------------------------------------------------------------

    def _check_args(self, ld: LaunchDescription) -> List[Issue]:
        issues = []
        counter = [0]

        def _issue_id():
            counter[0] += 1
            return f"issue_{ld.launch_file_id}_arg_{counter[0]:03d}"

        for aid, action in ld.actions.items():
            if not isinstance(action, DeclareArgumentAction):
                continue

            if action.default_value is None or (
                action.default_value.type == SubstitutionType.LITERAL
                and action.default_value.value is None
            ):
                context = {
                    "arg_name": action.name,
                }

                issue = self._make_issue(
                    key="arg_no_default",
                    issue_id=_issue_id(),
                    entity_id=aid,
                    context=context,
                    location=self._source_location(action),
                    metadata=context,
                )

                if issue:
                    issues.append(issue)

            if action.provenance and action.provenance.confidence < 0.9:
                context = {
                    "arg_name": action.name,
                    "confidence": action.provenance.confidence,
                }

                issue = self._make_issue(
                    key="arg_orphan",
                    issue_id=_issue_id(),
                    entity_id=aid,
                    context=context,
                    location=self._source_location(action),
                    metadata=context,
                )

                if issue:
                    issues.append(issue)

        return issues

    # -----------------------------------------------------------------------
    # Namespace
    # -----------------------------------------------------------------------

    def _check_namespace(self, ld: LaunchDescription) -> List[Issue]:
        issues = []
        counter = [0]

        def _issue_id():
            counter[0] += 1
            return f"issue_{ld.launch_file_id}_ns_{counter[0]:03d}"

        has_push_ns = any(
            isinstance(action, PushNamespaceAction)
            for action in ld.actions.values()
        )

        if not has_push_ns:
            return issues

        for aid, action in ld.actions.items():
            if not isinstance(action, NodeAction):
                continue

            if action.namespace or action.conditions:
                continue

            node_context = self._node_context(action)

            issue = self._make_issue(
                key="namespace_implicit",
                issue_id=_issue_id(),
                entity_id=aid,
                context=node_context,
                location=self._source_location(action),
                metadata=node_context,
            )

            if issue:
                issues.append(issue)

        return issues