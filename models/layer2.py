"""
layer2.py

Modelo Intermédio Layer 2 — HAROS ROS2
Implementação conforme a especificação haros_layer2.md

Classes:
    LaunchSubstitution      — valor simbólico (literal, arg_ref, env_var, file_path, expression)
    SourceRef               — localização num ficheiro fonte (conforme HAROS Common Types)
    ElementProvenance       — proveniência completa de um elemento (conforme HAROS Common Types)
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
class SourceRef:
    """
    Representa uma localização específica num ficheiro fonte.
    Conforme a especificação HAROS Common Types.
    """
    file_path: str                      # caminho relativo ao workspace
    line_start: Optional[int] = None    # linha inicial (1-indexed)
    line_end: Optional[int] = None      # linha final (inclusive)
    column_start: Optional[int] = None  # coluna inicial (1-indexed)
    column_end: Optional[int] = None    # coluna final (inclusive)
    note: Optional[str] = None          # nota explicativa

    def to_dict(self) -> dict:
        d = {"file_path": self.file_path}
        if self.line_start is not None:
            d["line_start"] = self.line_start
        if self.line_end is not None:
            d["line_end"] = self.line_end
        if self.column_start is not None:
            d["column_start"] = self.column_start
        if self.column_end is not None:
            d["column_end"] = self.column_end
        if self.note:
            d["note"] = self.note
        return d


# Alias para compatibilidade com código antigo
SourceLocation = SourceRef


@dataclass
class ElementProvenance:
    """
    Representa como uma entidade foi descoberta ou derivada.
    Conforme a especificação HAROS Common Types.

    Extraction methods:
        static_analysis   — análise do código fonte sem execução
        runtime_discovery — observado em sistema em execução
        annotation        — especificado manualmente
        composition       — derivado combinando outras entidades
        heuristic         — inferido por pattern matching

    Confidence scale:
        1.0        — observado em runtime ou ground truth
        0.9-0.99   — análise estática de padrões claros
        0.7-0.89   — análise estática com complexidade moderada
        0.5-0.69   — fluxo de controlo/dados complexo
        0.3-0.49   — inferência heurística
        < 0.3      — especulativo
    """
    extraction_method: str = "static_analysis"
    confidence: float = 1.0
    source_location: Optional[SourceRef] = None
    additional_locations: List[Any] = field(default_factory=list)
    extractor_version: Optional[str] = None
    extraction_timestamp: Optional[str] = None   # ISO 8601
    extraction_context: Dict[str, Any] = field(default_factory=dict)
    notes: Optional[str] = None

    VALID_METHODS = {
        "static_analysis", "runtime_discovery",
        "annotation", "composition", "heuristic"
    }

    def to_dict(self) -> dict:
        d = {
            "extraction_method": self.extraction_method,
            "confidence": self.confidence,
        }
        if self.source_location:
            d["source_location"] = self.source_location.to_dict()
        if self.additional_locations:
            d["additional_locations"] = [
                loc.to_dict() if hasattr(loc, "to_dict") else loc
                for loc in self.additional_locations
            ]
        if self.extractor_version:
            d["extractor_version"] = self.extractor_version
        if self.extraction_timestamp:
            d["extraction_timestamp"] = self.extraction_timestamp
        if self.extraction_context:
            d["extraction_context"] = self.extraction_context
        if self.notes:
            d["notes"] = self.notes
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
            fname = os.path.basename(self.provenance.source_location.file_path)
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
        cond = f"   [if: {action.conditions[0]}]" if action.conditions else ""

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
            clean = _re.sub(r"^launch_desc_file_", "", inc_id)
            # Caso 1: nome simples (sem vars) — converter underscores para extensão
            clean = _re.sub(r"_launch_py$", ".launch.py", clean)
            clean = _re.sub(r"_launch_xml$", ".launch.xml", clean)
            clean = _re.sub(r"_launch_yaml$", ".launch.yaml", clean)
            if "type" not in clean and "var" not in clean:
                fname = clean
            else:
                # Caso 2: os.path.join(var, ..., 'file.launch.py')
                # Tentar extrair o nome do ficheiro do final do ID
                m = _re.search(r"_____([a-z][a-z0-9_]+_launch(?:_py|_xml|_yaml)?)__+$", inc_id)
                if m:
                    fname = m.group(1)
                    fname = _re.sub(r"_launch_py$", ".launch.py", fname)
                    fname = _re.sub(r"_launch_xml$", ".launch.xml", fname)
                    fname = _re.sub(r"_launch_yaml$", ".launch.yaml", fname)
                else:
                    # fallback: mostrar só o que vem depois do último separador
                    m2 = _re.search(r"[a-z][a-z0-9_]+\.launch(?:\.py|\.xml|\.yaml)?$", clean)
                    fname = m2.group(0) if m2 else trunc(clean, 70)
            print(f"{pad}INCLUDE   {trunc(fname, 70)}{cond}")
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
            print(f"{pad}SET       {action.name} = {val}{scope}{cond}")
            print()

        elif isinstance(action, NodeAction):
            exe = action.executable.display() if action.executable else "?"
            print(f"{pad}EXEC      {exe}{cond}")
            print()


def __getattr__(name):
    """
    Compatibilidade temporária com imports antigos.

    Permite que código antigo como:
        from models.layer2 import IssueDetector
        from models.layer2 import Layer2Validator

    continue a funcionar durante a transição.
    """

    if name in {"Issue", "ElementRef"}:
        from models.layer6 import Issue, ElementRef
        return {
            "Issue": Issue,
            "ElementRef": ElementRef,
        }[name]

    if name == "IssueDetector":
        from issues.detector import IssueDetector
        return IssueDetector

    if name in {"Layer2Validator", "ValidationError"}:
        from validation.layer2_validator import Layer2Validator, ValidationError
        return {
            "Layer2Validator": Layer2Validator,
            "ValidationError": ValidationError,
        }[name]

    raise AttributeError(f"module 'models.layer2' has no attribute '{name}'")