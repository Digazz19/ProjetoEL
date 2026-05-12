#!/usr/bin/env python3

import json
import sys
from pathlib import Path


def extract_layer2(path: Path):
    if path.name.endswith(".launch.py"):
        from parsers.python.parser import PythonLaunchParser
        parser = PythonLaunchParser()
        tree, ld = parser.parse(str(path))
        return ld

    if path.name.endswith(".launch.xml"):
        from parsers.xml.parser import XMLLaunchParser
        parser = XMLLaunchParser()
        tree, ld = parser.parse(str(path))
        return ld

    if path.name.endswith(".launch.yaml") or path.name.endswith(".launch.yml"):
        from parsers.yaml.parser import YAMLLaunchParser
        parser = YAMLLaunchParser()
        tree, ld = parser.parse(str(path))
        return ld

    raise ValueError(f"Formato não suportado: {path}")


def to_dict(obj):
    if hasattr(obj, "to_dict"):
        return obj.to_dict()

    if hasattr(obj, "model_dump"):
        return obj.model_dump()

    if isinstance(obj, dict):
        return obj

    raise TypeError(f"Não sei converter objeto para dict: {type(obj)}")


def validate_layer2(layer2_obj):
    try:
        from validation.layer2_validator import Layer2Validator
    except ImportError:
        print("  [WARN] Não consegui importar models.layer2.Layer2Validator")
        return True, []

    validator = Layer2Validator()
    errors = validator.validate(layer2_obj)
    return len(errors) == 0, errors


EXPECTED = {
    # Primeira vaga
    "node": {
        "required_action_types": {"node"},
    },
    "args": {
        "required_action_types": {"declare_argument", "node"},
    },
    "params": {
        "required_action_types": {"node"},
        "node_must_have": ["parameters"],
    },
    "remaps": {
        "required_action_types": {"node"},
        "node_must_have": ["remappings"],
    },
    "group_namespace": {
        "required_action_types": {"group", "push_namespace", "node"},
    },
    "include": {
        "required_action_types": {"include"},
    },

    # Segunda vaga
    "conditions": {
        "required_action_types": {"declare_argument", "node"},
        "some_action_must_have": ["conditions"],
    },
    "substitutions_arg": {
        "required_action_types": {"declare_argument", "group", "push_namespace", "node"},
    },
    "env": {
        "required_action_types": {"set_parameter", "node"},
    },
    "nested_groups": {
        "required_action_types": {"group", "push_namespace", "node"},
    },

    # Cobertura HAROS Layer 2
    "group_set_params": {
        "required_action_types": {"group", "set_parameter", "node"},
    },
    "include_args": {
        "required_action_types": {"include"},
        "some_action_must_have": ["argument_mappings"],
    },
    "condition_and": {
        "required_action_types": {"declare_argument", "node"},
        "condition_operator": "and",
    },
    "condition_or": {
        "required_action_types": {"declare_argument", "node"},
        "condition_operator": "or",
    },
    "condition_not": {
        "required_action_types": {"declare_argument", "node"},
        "condition_operator": "not",
    },
    "filepath_substitution": {
        "required_action_types": {"node"},
        "some_action_must_have_nested": ["file_path"],
    },

    "environment_substitution": {
        "required_action_types": {"node"},
        "some_action_must_have_nested": ["environment_variable"],
    },

    "stable_id_a": {
        "required_action_types": {"node"},
    },

    "stable_id_b": {
        "required_action_types": {"node"},
    },
}


def detect_case(path: Path) -> str:
    return path.name.split(".launch.")[0]


def get_actions(layer2_dict):
    actions = layer2_dict.get("actions", {})
    if isinstance(actions, dict):
        return list(actions.values())
    if isinstance(actions, list):
        return actions
    return []


def contains_nested_value(obj, value):
    if obj == value:
        return True

    if isinstance(obj, dict):
        return any(contains_nested_value(v, value) for v in obj.values())

    if isinstance(obj, list):
        return any(contains_nested_value(v, value) for v in obj)

    return False


def has_condition_operator(actions, operator):
    for action in actions:
        for cond in action.get("conditions", []):
            if isinstance(cond, list) and cond and cond[0] == operator:
                return True
    return False


def check_basic_shape(layer2_dict):
    errors = []

    for field in ["id", "launch_file_id", "format", "actions", "launch_sequence", "provenance"]:
        if field not in layer2_dict:
            errors.append(f"campo obrigatório em falta: {field}")

    if "actions" in layer2_dict and not isinstance(layer2_dict["actions"], dict):
        errors.append("campo actions deve ser um dicionário/mapa")

    if "launch_sequence" in layer2_dict and not isinstance(layer2_dict["launch_sequence"], list):
        errors.append("campo launch_sequence deve ser uma lista")

    return errors


def check_expected_features(path: Path, layer2_dict):
    errors = []
    case = detect_case(path)
    spec = EXPECTED.get(case)

    if not spec:
        return errors

    actions = get_actions(layer2_dict)
    action_types = {a.get("action_type") for a in actions}

    missing = spec["required_action_types"] - action_types
    if missing:
        errors.append(
            f"tipos de ação em falta: {sorted(missing)}; encontrados: {sorted(action_types)}"
        )

    node_actions = [a for a in actions if a.get("action_type") == "node"]

    for required_field in spec.get("node_must_have", []):
        if not any(required_field in node for node in node_actions):
            errors.append(f"nenhum node contém o campo esperado: {required_field}")

    for required_field in spec.get("some_action_must_have", []):
        if not any(required_field in action for action in actions):
            errors.append(f"nenhuma ação contém o campo esperado: {required_field}")

    for required_nested_value in spec.get("some_action_must_have_nested", []):
        if not any(contains_nested_value(action, required_nested_value) for action in actions):
            errors.append(f"nenhuma ação contém valor nested esperado: {required_nested_value}")

    op = spec.get("condition_operator")
    if op and not has_condition_operator(actions, op):
        errors.append(f"operador condição não encontrado: {op}")

    return errors


def run_one(path: Path, output_dir: Path):
    print(f"\n==> {path}")

    try:
        layer2_obj = extract_layer2(path)
    except Exception as e:
        print(f"  [FAIL] extração falhou: {type(e).__name__}: {e}")
        return False

    try:
        layer2_dict = to_dict(layer2_obj)
    except Exception as e:
        print(f"  [FAIL] conversão para dict falhou: {type(e).__name__}: {e}")
        return False

    output_dir.mkdir(parents=True, exist_ok=True)
    out_file = output_dir / f"{path.name}.layer2.json"

    with out_file.open("w", encoding="utf-8") as f:
        json.dump(layer2_dict, f, indent=2, ensure_ascii=False)

    print(f"  [OK] JSON gerado: {out_file}")

    errors = []
    errors.extend(check_basic_shape(layer2_dict))
    errors.extend(check_expected_features(path, layer2_dict))

    try:
        valid, validation_errors = validate_layer2(layer2_obj)
        if not valid:
            errors.extend([f"Layer2Validator: {e}" for e in validation_errors])
    except Exception as e:
        errors.append(f"Layer2Validator lançou exceção: {type(e).__name__}: {e}")

    if errors:
        print("  [FAIL] problemas encontrados:")
        for err in errors:
            print(f"    - {err}")
        return False

    print("  [OK] válido nos testes básicos")
    return True


def main():
    if len(sys.argv) < 2:
        print("uso: python3 test_layer2.py examples/layer2-minimal")
        sys.exit(2)

    examples_dir = Path(sys.argv[1])
    output_dir = Path("output/layer2-tests")

    if not examples_dir.exists():
        print(f"diretoria não existe: {examples_dir}")
        sys.exit(2)

    files = sorted(
        list(examples_dir.glob("*.launch.xml"))
        + list(examples_dir.glob("*.launch.yaml"))
        + list(examples_dir.glob("*.launch.yml"))
        + list(examples_dir.glob("*.launch.py"))
    )

    if not files:
        print(f"nenhum launch file encontrado em {examples_dir}")
        sys.exit(2)

    passed = 0
    failed = 0

    for path in files:
        ok = run_one(path, output_dir)
        if ok:
            passed += 1
        else:
            failed += 1

    print("\n==============================")
    print(f"PASS: {passed}")
    print(f"FAIL: {failed}")
    print("==============================")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()