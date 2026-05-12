from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional

from models.layer2 import (
    ActionType,
    IncludeAction,
    LaunchDescription,
    NodeAction,
)


@dataclass
class ValidationError:
    severity: str  # "error" | "warning"
    rule: str
    message: str
    action_id: Optional[str] = None

    def __str__(self):
        loc = f" [{self.action_id}]" if self.action_id else ""
        return f"[{self.severity.upper()}] {self.rule}{loc}: {self.message}"


class Layer2Validator:
    """
    Valida um LaunchDescription contra as regras da especificação Layer 2.

    Regras implementadas:
    - actions_map_consistency
    - sequence_validity
    - reachability
    - no_orphans
    - id_format
    - no_cycles
    - scope_actions_only
    - node_required_fields
    - include_required_fields
    """

    ID_PATTERN = re.compile(r"^la:[a-zA-Z0-9_]+:[0-9a-f]{8}#\d+$")

    def validate(self, ld: LaunchDescription) -> List[ValidationError]:
        errors = []
        errors.extend(self._check_actions_map_consistency(ld))
        errors.extend(self._check_sequence_validity(ld))

        reachable = self._compute_reachable(ld)

        errors.extend(self._check_reachability(ld, reachable))
        errors.extend(self._check_no_orphans(ld, reachable))
        errors.extend(self._check_id_format(ld))
        errors.extend(self._check_no_cycles(ld))
        errors.extend(self._check_scope_actions(ld))
        errors.extend(self._check_node_required_fields(ld))
        errors.extend(self._check_include_required_fields(ld))

        return errors

    def _check_actions_map_consistency(self, ld: LaunchDescription) -> List[ValidationError]:
        errors = []

        for key, action in ld.actions.items():
            if key != action.id:
                errors.append(ValidationError(
                    severity="error",
                    rule="actions_map_consistency",
                    message=f"Chave '{key}' não corresponde ao action id '{action.id}'",
                    action_id=key,
                ))

        return errors

    def _check_sequence_validity(self, ld: LaunchDescription) -> List[ValidationError]:
        errors = []

        for aid in ld.launch_sequence:
            if aid not in ld.actions:
                errors.append(ValidationError(
                    severity="error",
                    rule="sequence_validity",
                    message=f"ID '{aid}' na sequência não existe no mapa de acções",
                    action_id=aid,
                ))

        return errors

    def _compute_reachable(self, ld: LaunchDescription) -> set[str]:
        reachable = set()

        def visit(aid: str):
            if aid in reachable or aid not in ld.actions:
                return

            reachable.add(aid)
            action = ld.actions[aid]

            for child in getattr(action, "children", []):
                visit(child)

        for aid in ld.launch_sequence:
            visit(aid)

        return reachable

    def _check_reachability(
        self,
        ld: LaunchDescription,
        reachable: set[str],
    ) -> List[ValidationError]:
        errors = []

        for aid in ld.launch_sequence:
            if aid not in ld.actions:
                continue

            if aid not in reachable:
                errors.append(ValidationError(
                    severity="warning",
                    rule="reachability",
                    message=f"Acção '{aid}' está na sequência mas não é alcançável",
                    action_id=aid,
                ))

        return errors

    def _check_no_orphans(
        self,
        ld: LaunchDescription,
        reachable: set[str],
    ) -> List[ValidationError]:
        errors = []

        for aid in ld.actions:
            if aid not in reachable:
                errors.append(ValidationError(
                    severity="warning",
                    rule="no_orphans",
                    message=f"Acção '{aid}' existe no mapa mas não é alcançável",
                    action_id=aid,
                ))

        return errors

    def _check_id_format(self, ld: LaunchDescription) -> List[ValidationError]:
        errors = []

        for aid in ld.actions:
            if not self.ID_PATTERN.match(aid):
                errors.append(ValidationError(
                    severity="error",
                    rule="id_format",
                    message=f"ID '{aid}' não segue o formato la:<file_id>:<hash>#<ordinal>",
                    action_id=aid,
                ))

        return errors

    def _check_no_cycles(self, ld: LaunchDescription) -> List[ValidationError]:
        errors = []
        visited = set()
        path = set()

        def dfs(aid: str):
            if aid in path:
                errors.append(ValidationError(
                    severity="error",
                    rule="no_cycles",
                    message=f"Ciclo detectado envolvendo acção '{aid}'",
                    action_id=aid,
                ))
                return

            if aid in visited or aid not in ld.actions:
                return

            visited.add(aid)
            path.add(aid)

            action = ld.actions[aid]
            for child in getattr(action, "children", []):
                dfs(child)

            path.discard(aid)

        for aid in ld.launch_sequence:
            dfs(aid)

        return errors

    def _check_scope_actions(self, ld: LaunchDescription) -> List[ValidationError]:
        errors = []
        scope_types = {
            ActionType.PUSH_NAMESPACE,
            ActionType.GROUP,
            ActionType.INCLUDE,
        }

        for aid, action in ld.actions.items():
            children = getattr(action, "children", [])

            if children and action.action_type not in scope_types:
                errors.append(ValidationError(
                    severity="error",
                    rule="scope_actions_only",
                    message=(
                        f"Acção do tipo '{action.action_type.value}' tem children "
                        f"mas não é push_namespace/group/include"
                    ),
                    action_id=aid,
                ))

        return errors

    def _check_node_required_fields(self, ld: LaunchDescription) -> List[ValidationError]:
        errors = []

        for aid, action in ld.actions.items():
            if isinstance(action, NodeAction):
                if not action.package:
                    errors.append(ValidationError(
                        severity="error",
                        rule="node_required_fields",
                        message="NodeAction não tem package",
                        action_id=aid,
                    ))

                if not action.executable:
                    errors.append(ValidationError(
                        severity="error",
                        rule="node_required_fields",
                        message="NodeAction não tem executable",
                        action_id=aid,
                    ))

        return errors

    def _check_include_required_fields(self, ld: LaunchDescription) -> List[ValidationError]:
        errors = []

        for aid, action in ld.actions.items():
            if isinstance(action, IncludeAction):
                if not action.included_launch_id:
                    errors.append(ValidationError(
                        severity="error",
                        rule="include_required_fields",
                        message="IncludeAction não tem included_launch_id",
                        action_id=aid,
                    ))

        return errors