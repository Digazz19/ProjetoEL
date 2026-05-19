#!/bin/bash

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

echo "======================================"
echo "  DEMO ProjetoEL Completa"
echo "======================================"

echo
echo "======================================"
echo "  0. Limpeza de outputs antigos"
echo "======================================"
rm -rf output
mkdir -p output

echo
echo "======================================"
echo "  1. Compilação Python"
echo "======================================"
python3 -m py_compile \
  main.py \
  test_layer2.py \
  test_launchfiles.py \
  models/layer2.py \
  models/layer6.py \
  models/runtime_architecture.py \
  validation/layer2_validator.py \
  issues/catalog.py \
  issues/detector.py \
  issues/graphdb_detector.py \
  issues/io.py \
  issues/ontology_detector.py \
  parsers/python/transformerPython.py \
  parsers/xml/transformerXML.py \
  parsers/yaml/transformerYAML.py \
  scripts/ontology/export_layer2_to_rdf.py \
  scripts/ontology/export_all_layer2_to_rdf.py \
  scripts/ontology/run_ontology_issues.py \
  scripts/ontology/run_all_ontology_pipeline.py \
  scripts/ontology/validate_rdf.py \
  scripts/ontology/validate_all_rdf.py \
  scripts/graphdb/graphdb_clear.py \
  scripts/graphdb/graphdb_query.py \
  scripts/graphdb/graphdb_upload.py \
  scripts/graphdb/run_graphdb_issues.py \
  scripts/communication/build_runtime_architecture.py \
  scripts/communication/export_architecture_to_rdf.py \
  scripts/communication/run_communication_issues.py \
  scripts/communication/run_communication_pipeline.py

echo
echo "======================================"
echo "  2. Testes Layer 2 mínimos"
echo "======================================"
python3 test_layer2.py examples/layer2-minimal

echo
echo "======================================"
echo "  3. Testes de cobertura HAROS Layer 2"
echo "======================================"
python3 test_layer2.py examples/layer2-haros-coverage

echo
echo "======================================"
echo "  4. Testes nos exemplos reais Python"
echo "======================================"
python3 test_launchfiles.py examples/real-python

echo
echo "======================================"
echo "  5. Pipeline ontológico Layer 2"
echo "======================================"
python3 scripts/ontology/run_all_ontology_pipeline.py output

echo
echo "======================================"
echo "  6. Validação SHACL Layer 2"
echo "======================================"
python3 scripts/ontology/validate_all_rdf.py

echo
echo "======================================"
echo "  7. Gerar Layer 2 dos exemplos de comunicação"
echo "======================================"
python3 main.py python examples/communication/communication_demo.launch.py
python3 main.py python examples/communication/communication_remap.launch.py
python3 main.py python examples/real-python/robot.launch.py

echo
echo "======================================"
echo "  8. Pipeline de comunicação"
echo "======================================"
python3 scripts/communication/run_communication_pipeline.py \
  output/communication_demo.launch.layer2.json \
  node_interfaces/communication_demo.layer1.yaml

python3 scripts/communication/run_communication_pipeline.py \
  output/communication_remap.launch.layer2.json \
  node_interfaces/communication_remap.layer1.yaml

python3 scripts/communication/run_communication_pipeline.py \
  output/robot.launch.layer2.json \
  node_interfaces/robot.layer1.yaml

echo
echo "======================================"
echo "  9. Resumo de outputs gerados"
echo "======================================"

echo "JSONs Layer 2 em output/:"
find output -maxdepth 1 -name "*.layer2.json" | wc -l

echo "JSONs Layer 2 em output/layer2-tests/:"
find output/layer2-tests -name "*.layer2.json" | wc -l

echo "JSONs de arquitetura runtime em output/architecture/:"
find output/architecture -maxdepth 1 -name "*.architecture.json" 2>/dev/null | wc -l

echo "RDFs Layer 2 em output/rdf/:"
find output/rdf -maxdepth 1 -name "*.layer2.ttl" | wc -l

echo "RDFs de arquitetura em output/rdf/architecture/:"
find output/rdf/architecture -maxdepth 1 -name "*.architecture.ttl" 2>/dev/null | wc -l

echo "JSONs de issues estruturais em output/issues/:"
find output/issues -maxdepth 1 \
  -name "*.issues.json" \
  ! -name "*.ontology.issues.json" \
  ! -name "*.communication.issues.json" \
  ! -name "graphdb.issues.json" | wc -l

echo "JSONs de issues ontológicos em output/issues/:"
find output/issues -maxdepth 1 -name "*.ontology.issues.json" | wc -l

echo "JSONs de issues de comunicação em output/issues/:"
find output/issues -maxdepth 1 -name "*.communication.issues.json" | wc -l

echo
echo "======================================"
echo "  DEMO CONCLUÍDA COM SUCESSO"
echo "======================================"
