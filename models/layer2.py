"""
layer2.py

Modelo Intermédio Layer 2 — HAROS ROS2
Implementação conforme a especificação haros_layer2.md

Classes:
    LaunchSubstitution      — valor simbólico (literal, arg_ref, env_var, file_path, expression)
    ElementProvenance       — proveniência de um elemento (ficheiro, linha, método, confiança)
    LaunchAction            — acção base (abstract)
    DeclareArgumentAction   — declaração de argumento
    SetParameterAction      — definição de parâmetro
    PushNamespaceAction     — introdução de namespace
    NodeAction              — instanciação simbólica de node
    IncludeAction           — inclusão de outro launch file
    GroupAction             — agrupamento de acções com scope opcional
    LaunchDescription       — ponto de entrada de um launch file
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union


# ---------------------------------------------------------------------------
# LaunchSubstitution
# ---------------------------------------------------------------------------

class SubstitutionType(str, Enum):
    LITERAL             = "literal"
    ARGUMENT_REFERENCE  = "argument_reference"
    ENVIRONMENT_VARIABLE = "environment_variable"
    FILE_PATH           = "file_path"
    EXPRESSION          = "expression"


@dataclass
class LaunchSubstitution:
    """Valor simbólico que pode ser resolvido em runtime."""
    type: SubstitutionType
    # Campos dependentes do tipo
    value: Any = None                   # literal
    argument_name: Optional[str] = None # argument_reference
    default_value: Any = None           # argument_reference, environment_variable
    variable_name: Optional[str] = None # environment_variable
    package: Optional[str] = None       # file_path
    relative_path: Optional[str] = None # file_path
    expression: Any = None              # expression (IR tree)

    @staticmethod
    def literal(value: Any) -> "LaunchSubstitution":
        return LaunchSubstitution(type=SubstitutionType.LITERAL, value=value)

    @staticmethod
    def argument_reference(name: str, default: Any = None) -> "LaunchSubstitution":
        return LaunchSubstitution(
            type=SubstitutionType.ARGUMENT_REFERENCE,
            argument_name=name,
            default_value=default,
        )

    @staticmethod
    def environment_variable(name: str, default: Any = None) -> "LaunchSubstitution":
        return LaunchSubstitution(
            type=SubstitutionType.ENVIRONMENT_VARIABLE,
            variable_name=name,
            default_value=default,
        )

    @staticmethod
    def file_path(package: str, relative_path: str) -> "LaunchSubstitution":
        return LaunchSubstitution(
            type=SubstitutionType.FILE_PATH,
            package=package,
            relative_path=relative_path,
        )

    @staticmethod
    def expression(expr: Any) -> "LaunchSubstitution":
        return LaunchSubstitution(type=SubstitutionType.EXPRESSION, expression=expr)

    @staticmethod
    def from_raw(value: Any) -> "LaunchSubstitution":
        """Cria um LaunchSubstitution a partir de um valor raw do transformer."""
        if value is None:
            return LaunchSubstitution.literal(None)
        if isinstance(value, LaunchSubstitution):
            return value
        if isinstance(value, dict):
            t = value.get("type")
            if t == "var":
                return LaunchSubstitution.argument_reference(value.get("name", ""))
            if t == "launch_config":
                name = value.get("name", "")
                default = value.get("default")
                return LaunchSubstitution.argument_reference(name, default)
            if t == "env_var":
                return LaunchSubstitution.environment_variable(
                    value.get("name", ""), value.get("default")
                )
            if t == "file_path":
                return LaunchSubstitution.file_path(
                    value.get("package", ""), value.get("path", "")
                )
        # fallback — string simbólica
        return LaunchSubstitution.literal(str(value))

    def to_dict(self) -> dict:
        d = {"type": self.type.value}
        if self.type == SubstitutionType.LITERAL:
            d["value"] = self.value
        elif self.type == SubstitutionType.ARGUMENT_REFERENCE:
            d["argument_name"] = self.argument_name
            if self.default_value is not None:
                d["default_value"] = self.default_value
        elif self.type == SubstitutionType.ENVIRONMENT_VARIABLE:
            d["variable_name"] = self.variable_name
            if self.default_value is not None:
                d["default_value"] = self.default_value
        elif self.type == SubstitutionType.FILE_PATH:
            d["package"] = self.package
            d["relative_path"] = self.relative_path
        elif self.type == SubstitutionType.EXPRESSION:
            d["expression"] = self.expression
        return d

    def display(self) -> str:
        """Representação legível para o print_summary."""
        if self.type == SubstitutionType.LITERAL:
            return str(self.value)
        elif self.type == SubstitutionType.ARGUMENT_REFERENCE:
            default = f"={self.default_value}" if self.default_value is not None else ""
            return f"$(arg {self.argument_name}{default})"
        elif self.type == SubstitutionType.ENVIRONMENT_VARIABLE:
            default = f"={self.default_value}" if self.default_value is not None else ""
            return f"$(env {self.variable_name}{default})"
        elif self.type == SubstitutionType.FILE_PATH:
            return f"$(find-pkg-share {self.package})/{self.relative_path}"
        elif self.type == SubstitutionType.EXPRESSION:
            return f"$(expr {self.expression})"
        return str(self.to_dict())

    def __repr__(self):
        return json.dumps(self.to_dict(), ensure_ascii=False)


# ---------------------------------------------------------------------------
# ElementProvenance
# ---------------------------------------------------------------------------

@dataclass
class SourceLocation:
    file: str
    line: Optional[int] = None
    column: Optional[int] = None

    def to_dict(self) -> dict:
        d = {"file": self.file}
        if self.line is not None:
            d["line"] = self.line
        if self.column is not None:
            d["column"] = self.column
        return d


@dataclass
class ElementProvenance:
    extraction_method: str = "static_analysis"
    source_location: Optional[SourceLocation] = None
    confidence: float = 1.0

    def to_dict(self) -> dict:
        d = {
            "extraction_method": self.extraction_method,
            "confidence": self.confidence,
        }
        if self.source_location:
            d["source_location"] = self.source_location.to_dict()
        return d


# ---------------------------------------------------------------------------
# Action ID Generation
# ---------------------------------------------------------------------------

def _normalize_source(snippet: str) -> str:
    """Normaliza um snippet de código para hashing estável."""
    # Remover comentários
    snippet = re.sub(r'#[^\n]*', '', snippet)
    # Normalizar aspas simples para duplas
    snippet = snippet.replace("'", '"')
    # Remover whitespace
    snippet = re.sub(r'\s+', '', snippet)
    return snippet


def _compute_hash(normalized: str) -> str:
    """Calcula hash de 8 caracteres hex."""
    return hashlib.md5(normalized.encode()).hexdigest()[:8]


class ActionIDGenerator:
    """Gera IDs determinísticos para acções seguindo o formato la:<file_id>:<hash>#<ordinal>."""

    def __init__(self, file_id: str):
        self.file_id = file_id
        self._hash_counts: Dict[str, int] = {}

    def generate(self, source_snippet: str = "") -> str:
        normalized = _normalize_source(source_snippet) if source_snippet else ""
        h = _compute_hash(normalized) if normalized else "00000000"
        ordinal = self._hash_counts.get(h, 0)
        self._hash_counts[h] = ordinal + 1
        return f"la:{self.file_id}:{h}#{ordinal}"

    @staticmethod
    def file_id_from_path(file_path: str) -> str:
        """Gera um file_id a partir do caminho do ficheiro."""
        name = file_path.replace("/", "_").replace("\\", "_").replace(".", "_")
        # Remover caracteres inválidos
        name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        return f"file_{name}"


# ---------------------------------------------------------------------------
# LaunchAction (base)
# ---------------------------------------------------------------------------

class ActionType(str, Enum):
    DECLARE_ARGUMENT = "declare_argument"
    SET_PARAMETER    = "set_parameter"
    PUSH_NAMESPACE   = "push_namespace"
    NODE             = "node"
    INCLUDE          = "include"
    GROUP            = "group"


@dataclass
class LaunchAction:
    id: str
    action_type: ActionType
    conditions: List[Any] = field(default_factory=list)
    provenance: Optional[ElementProvenance] = None

    def to_dict(self) -> dict:
        d = {
            "id": self.id,
            "action_type": self.action_type.value,
        }
        if self.conditions:
            d["conditions"] = self.conditions
        if self.provenance:
            d["provenance"] = self.provenance.to_dict()
        return d


# ---------------------------------------------------------------------------
# DeclareArgumentAction
# ---------------------------------------------------------------------------

@dataclass
class DeclareArgumentAction(LaunchAction):
    name: str = ""
    default_value: Optional[LaunchSubstitution] = None
    description: Optional[str] = None
    choices: Optional[List[Any]] = None

    def __post_init__(self):
        self.action_type = ActionType.DECLARE_ARGUMENT

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["name"] = self.name
        if self.default_value is not None:
            d["default_value"] = self.default_value.to_dict()
        if self.description:
            d["description"] = self.description
        if self.choices:
            d["choices"] = self.choices
        return d


# ---------------------------------------------------------------------------
# SetParameterAction
# ---------------------------------------------------------------------------

@dataclass
class SetParameterAction(LaunchAction):
    name: str = ""
    value: Optional[LaunchSubstitution] = None
    target_scope: str = "local"

    def __post_init__(self):
        self.action_type = ActionType.SET_PARAMETER

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["name"] = self.name
        if self.value is not None:
            d["value"] = self.value.to_dict()
        d["target_scope"] = self.target_scope
        return d


# ---------------------------------------------------------------------------
# PushNamespaceAction
# ---------------------------------------------------------------------------

@dataclass
class PushNamespaceAction(LaunchAction):
    namespace: Optional[LaunchSubstitution] = None
    children: List[str] = field(default_factory=list)

    def __post_init__(self):
        self.action_type = ActionType.PUSH_NAMESPACE

    def to_dict(self) -> dict:
        d = super().to_dict()
        if self.namespace is not None:
            d["namespace"] = self.namespace.to_dict()
        d["children"] = self.children
        return d


# ---------------------------------------------------------------------------
# NodeAction
# ---------------------------------------------------------------------------

@dataclass
class Remapping:
    from_topic: str
    to_topic: LaunchSubstitution

    def to_dict(self) -> dict:
        return {
            "from": self.from_topic,
            "to": self.to_topic.to_dict(),
        }


@dataclass
class NodeAction(LaunchAction):
    package: Optional[LaunchSubstitution] = None
    executable: Optional[LaunchSubstitution] = None
    name: Optional[LaunchSubstitution] = None
    namespace: Optional[LaunchSubstitution] = None
    parameters: Dict[str, LaunchSubstitution] = field(default_factory=dict)
    remappings: List[Remapping] = field(default_factory=list)
    ros_arguments: List[str] = field(default_factory=list)
    launch_prefix: Optional[str] = None

    def __post_init__(self):
        self.action_type = ActionType.NODE

    def to_dict(self) -> dict:
        d = super().to_dict()
        if self.package:
            d["package"] = self.package.to_dict()
        if self.executable:
            d["executable"] = self.executable.to_dict()
        if self.name:
            d["name"] = self.name.to_dict()
        if self.namespace:
            d["namespace"] = self.namespace.to_dict()
        if self.parameters:
            d["parameters"] = {k: v.to_dict() for k, v in self.parameters.items()}
        if self.remappings:
            d["remappings"] = [r.to_dict() for r in self.remappings]
        if self.ros_arguments:
            d["ros_arguments"] = self.ros_arguments
        if self.launch_prefix:
            d["launch_prefix"] = self.launch_prefix
        return d


# ---------------------------------------------------------------------------
# IncludeAction
# ---------------------------------------------------------------------------

@dataclass
class IncludeAction(LaunchAction):
    included_launch_id: str = ""
    argument_mappings: Dict[str, LaunchSubstitution] = field(default_factory=dict)

    def __post_init__(self):
        self.action_type = ActionType.INCLUDE

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["included_launch_id"] = self.included_launch_id
        if self.argument_mappings:
            d["argument_mappings"] = {k: v.to_dict() for k, v in self.argument_mappings.items()}
        return d


# ---------------------------------------------------------------------------
# GroupAction
# ---------------------------------------------------------------------------

@dataclass
class GroupAction(LaunchAction):
    children: List[str] = field(default_factory=list)
    namespace: Optional[LaunchSubstitution] = None
    set_parameters: Dict[str, LaunchSubstitution] = field(default_factory=dict)

    def __post_init__(self):
        self.action_type = ActionType.GROUP

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["children"] = self.children
        if self.namespace:
            d["namespace"] = self.namespace.to_dict()
        if self.set_parameters:
            d["set_parameters"] = {k: v.to_dict() for k, v in self.set_parameters.items()}
        return d


# ---------------------------------------------------------------------------
# LaunchDescription
# ---------------------------------------------------------------------------

@dataclass
class LaunchDescription:
    id: str
    launch_file_id: str
    format: str  # python, xml, yaml
    actions: Dict[str, LaunchAction] = field(default_factory=dict)
    launch_sequence: List[str] = field(default_factory=list)
    provenance: Optional[ElementProvenance] = None

    def add_action(self, action: LaunchAction, to_sequence: bool = True):
        """Adiciona uma acção ao mapa e opcionalmente à sequência."""
        self.actions[action.id] = action
        if to_sequence and action.id not in self.launch_sequence:
            self.launch_sequence.append(action.id)

    def to_dict(self) -> dict:
        d = {
            "id": self.id,
            "launch_file_id": self.launch_file_id,
            "format": self.format,
            "actions": {k: v.to_dict() for k, v in self.actions.items()},
            "launch_sequence": self.launch_sequence,
        }
        if self.provenance:
            d["provenance"] = self.provenance.to_dict()
        return d

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @staticmethod
    def _short_id(action_id: str) -> str:
        import re
        m = re.search(r':([0-9a-f]{8})#(\d+)$', action_id)
        if m:
            ordinal = f".{m.group(2)}" if int(m.group(2)) > 0 else ""
            return f"#{m.group(1)}{ordinal}"
        return action_id

    def print_summary(self):
        """Imprime um resumo legível e formatado do LaunchDescription."""
        import os
        W = 110

        if self.provenance and self.provenance.source_location:
            fname = os.path.basename(self.provenance.source_location.file)
        else:
            fname = self.launch_file_id

        def trunc(s, n):
            s = str(s) if s is not None else ""
            return s if len(s) <= n else s[:n-1] + "…"

        # Cabeçalho
        print(f"\n  {'═' * W}")
        print(f"  {fname}  ·  {self.format.upper()}  ·  {len(self.actions)} acções  ·  seq={len(self.launch_sequence)}")
        print(f"  {'═' * W}\n")

        # Separar por tipo
        args, others = [], []
        for aid in self.launch_sequence:
            a = self.actions.get(aid)
            if a is None: continue
            if isinstance(a, DeclareArgumentAction):
                args.append(a)
            else:
                others.append(a)

        # ─── ARGUMENTOS ────────────────────────────────────────
        if args:
            NAME_W = max((len(a.name) for a in args), default=12)
            NAME_W = min(max(NAME_W, 14), 28)
            DV_W = 30
            DESC_W = W - NAME_W - DV_W - 8

            sep_top    = f"  ┌{'─' * (NAME_W + 2)}┬{'─' * (DV_W + 2)}┬{'─' * (DESC_W + 2)}┐"
            sep_middle = f"  ├{'─' * (NAME_W + 2)}┼{'─' * (DV_W + 2)}┼{'─' * (DESC_W + 2)}┤"
            sep_bot    = f"  └{'─' * (NAME_W + 2)}┴{'─' * (DV_W + 2)}┴{'─' * (DESC_W + 2)}┘"

            print(f"\n  ARGUMENTOS")
            print(sep_top)
            print(f"  │ {'NOME':<{NAME_W}} │ {'DEFAULT':<{DV_W}} │ {'DESCRIÇÃO':<{DESC_W}} │")
            print(sep_middle)
            for a in args:
                name = trunc(a.name, NAME_W)
                dv = a.default_value.display() if a.default_value else "—"
                dv = trunc(dv, DV_W)
                desc = trunc(a.description or "", DESC_W)
                if a.choices and len(desc) + len(', '.join(a.choices)) + 4 < DESC_W:
                    desc += f" [{', '.join(a.choices)}]"
                print(f"  │ {name:<{NAME_W}} │ {dv:<{DV_W}} │ {desc:<{DESC_W}} │")
            print(sep_bot)
            print()

        # ─── ACÇÕES ────────────────────────────────────────────
        if others:
            print(f"  ACÇÕES PRINCIPAIS")
            print(f"  {'─' * W}")
            for action in others:
                self._print_action(action, indent=2)

        # ─── ACÇÕES FILHAS ─────────────────────────────────────
        orphans = [a for aid, a in self.actions.items()
                   if aid not in self.launch_sequence]
        if orphans:
            print(f"  ACÇÕES FILHAS  ({len(orphans)})")
            print(f"  {'─' * W}")
            for action in orphans:
                self._print_action(action, indent=2)

    def _print_action(self, action: LaunchAction, indent: int = 4):
        pad = " " * indent
        detail_pad = " " * (indent + 10)
        cond = f"   [if {action.conditions[0]}]" if action.conditions else ""

        def trunc(s, n):
            s = str(s) if s is not None else ""
            return s if len(s) <= n else s[:n-1] + "…"

        if isinstance(action, NodeAction) and action.package and action.package.value != "__executable__":
            pkg = action.package.display() if action.package else "?"
            exe = action.executable.display() if action.executable else "?"
            name = action.name.display() if action.name else None
            ns = action.namespace.display() if action.namespace else None
            title = f"{pkg} / {exe}"
            if name:
                title += f"   [{name}]"
            if ns:
                title += f"   ns={ns}"
            print(f"{pad}NODE      {title}{cond}")
            for r in action.remappings or []:
                frm = r.from_topic
                to = r.to_topic.display()
                print(f"{detail_pad}remap    {frm}  →  {to}")
            for k, v in (action.parameters or {}).items():
                print(f"{detail_pad}param    {k} = {v.display()}")
            if action.ros_arguments:
                args_str = " ".join(action.ros_arguments)
                print(f"{detail_pad}args     {args_str}")
            print()

        elif isinstance(action, IncludeAction):
            import re as _re
            inc_id = action.included_launch_id
            m = _re.search(r'file_(.+)', inc_id)
            fname = m.group(1).replace('_', '/').strip('/') if m else inc_id
            print(f"{pad}INCLUDE   {trunc(fname, 60)}{cond}")
            for k, v in (action.argument_mappings or {}).items():
                print(f"{detail_pad}arg      {k} = {v.display()}")
            print()

        elif isinstance(action, GroupAction):
            ns = action.namespace.display() if action.namespace else "—"
            print(f"{pad}GROUP     ns={ns}   ({len(action.children)} filhos){cond}")
            print()

        elif isinstance(action, PushNamespaceAction):
            ns = action.namespace.display() if action.namespace else "—"
            print(f"{pad}PUSH_NS   {ns}{cond}")
            print()

        elif isinstance(action, SetParameterAction):
            scope = f"   [{action.target_scope}]" if action.target_scope != "local" else ""
            val = action.value.display() if action.value else "—"
            print(f"{pad}SET       {action.name} = {val}{scope}")
            print()

        elif isinstance(action, NodeAction):
            exe = action.executable.display() if action.executable else "?"
            print(f"{pad}EXEC      {exe}{cond}")
            print()


# ---------------------------------------------------------------------------
# Validador Layer 2
# ---------------------------------------------------------------------------

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
    - actions_map_consistency: chaves == action ids
    - sequence_validity: todos os IDs da sequência existem no mapa
    - reachability: todas as acções são alcançáveis
    - no_orphans: nenhuma acção existe sem ser alcançável
    - id_format: IDs seguem o formato la:<file_id>:<hash>#<ordinal>
    - no_cycles: a árvore de acções é acíclica
    - scope_actions_only: só push_namespace, group, include têm children
    - node_required_fields: NodeAction tem package e executable
    - include_required_fields: IncludeAction tem included_launch_id
    """

    ID_PATTERN = re.compile(r'^la:[a-zA-Z0-9_]+:[0-9a-f]{8}#\d+$')

    def validate(self, ld: "LaunchDescription") -> List[ValidationError]:
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

    def _check_actions_map_consistency(self, ld):
        errors = []
        for key, action in ld.actions.items():
            if key != action.id:
                errors.append(ValidationError(
                    severity="error", rule="actions_map_consistency",
                    message=f"Chave '{key}' não corresponde ao action id '{action.id}'",
                    action_id=key,
                ))
        return errors

    def _check_sequence_validity(self, ld):
        errors = []
        for aid in ld.launch_sequence:
            if aid not in ld.actions:
                errors.append(ValidationError(
                    severity="error", rule="sequence_validity",
                    message=f"ID '{aid}' na sequência não existe no mapa de acções",
                    action_id=aid,
                ))
        return errors

    def _compute_reachable(self, ld) -> set:
        reachable = set()
        def visit(aid):
            if aid in reachable or aid not in ld.actions:
                return
            reachable.add(aid)
            action = ld.actions[aid]
            children = getattr(action, 'children', [])
            for child in children:
                visit(child)
        for aid in ld.launch_sequence:
            visit(aid)
        return reachable

    def _check_reachability(self, ld, reachable):
        errors = []
        for aid in ld.launch_sequence:
            if aid not in ld.actions:
                continue  # já reportado em sequence_validity
            if aid not in reachable:
                errors.append(ValidationError(
                    severity="warning", rule="reachability",
                    message=f"Acção '{aid}' está na sequência mas não é alcançável",
                    action_id=aid,
                ))
        return errors

    def _check_no_orphans(self, ld, reachable):
        errors = []
        for aid in ld.actions:
            if aid not in reachable:
                errors.append(ValidationError(
                    severity="warning", rule="no_orphans",
                    message=f"Acção '{aid}' existe no mapa mas não é alcançável",
                    action_id=aid,
                ))
        return errors

    def _check_id_format(self, ld):
        errors = []
        for aid in ld.actions:
            if not self.ID_PATTERN.match(aid):
                errors.append(ValidationError(
                    severity="error", rule="id_format",
                    message=f"ID '{aid}' não segue o formato la:<file_id>:<hash>#<ordinal>",
                    action_id=aid,
                ))
        return errors

    def _check_no_cycles(self, ld):
        errors = []
        visited = set()
        path = set()

        def dfs(aid):
            if aid in path:
                errors.append(ValidationError(
                    severity="error", rule="no_cycles",
                    message=f"Ciclo detectado envolvendo acção '{aid}'",
                    action_id=aid,
                ))
                return
            if aid in visited or aid not in ld.actions:
                return
            visited.add(aid)
            path.add(aid)
            action = ld.actions[aid]
            for child in getattr(action, 'children', []):
                dfs(child)
            path.discard(aid)

        for aid in ld.launch_sequence:
            dfs(aid)
        return errors

    def _check_scope_actions(self, ld):
        errors = []
        scope_types = {ActionType.PUSH_NAMESPACE, ActionType.GROUP, ActionType.INCLUDE}
        for aid, action in ld.actions.items():
            children = getattr(action, 'children', [])
            if children and action.action_type not in scope_types:
                errors.append(ValidationError(
                    severity="error", rule="scope_actions_only",
                    message=f"Acção do tipo '{action.action_type.value}' tem children mas não é push_namespace/group/include",
                    action_id=aid,
                ))
        return errors

    def _check_node_required_fields(self, ld):
        errors = []
        for aid, action in ld.actions.items():
            if isinstance(action, NodeAction):
                if not action.package:
                    errors.append(ValidationError(
                        severity="error", rule="node_required_fields",
                        message="NodeAction não tem package",
                        action_id=aid,
                    ))
                if not action.executable:
                    errors.append(ValidationError(
                        severity="error", rule="node_required_fields",
                        message="NodeAction não tem executable",
                        action_id=aid,
                    ))
        return errors

    def _check_include_required_fields(self, ld):
        errors = []
        for aid, action in ld.actions.items():
            if isinstance(action, IncludeAction):
                if not action.included_launch_id:
                    errors.append(ValidationError(
                        severity="error", rule="include_required_fields",
                        message="IncludeAction não tem included_launch_id",
                        action_id=aid,
                    ))
        return errors