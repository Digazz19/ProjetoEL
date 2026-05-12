#!/bin/bash

set -e

echo "======================================"
echo "  DEMO ProjetoEL Layer 2"
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
  validation/layer2_validator.py \
  issues/catalog.py \
  issues/detector.py \
  issues/io.py \
  issues/ontology_detector.py \
  parsers/python/transformerPython.py \
  parsers/xml/transformerXML.py \
  parsers/yaml/transformerYAML.py \
  scripts/export_layer2_to_rdf.py \
  scripts/run_ontology_issues.py \
  scripts/run_all_ontology_pipeline.py

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
echo "  5. Pipeline ontológico completo"
echo "======================================"
python3 scripts/run_all_ontology_pipeline.py output

echo
echo "======================================"
echo "  6. Validação SHACL"
echo "======================================"
python3 scripts/validate_all_rdf.py

echo
echo "======================================"
echo "  7. Resumo de outputs gerados"
echo "======================================"
echo "JSONs Layer 2 em output/:"
find output -maxdepth 1 -name "*.layer2.json" | wc -l

echo "JSONs Layer 2 em output/layer2-tests/:"
find output/layer2-tests -name "*.layer2.json" | wc -l

echo "RDFs Layer 2 em output/rdf/:"
find output/rdf -maxdepth 1 -name "*.ttl" | wc -l

echo "JSONs de issues estruturais em output/issues/:"
find output/issues -maxdepth 1 -name "*.issues.json" ! -name "*.ontology.issues.json" | wc -l

echo "JSONs de issues ontológicos em output/issues/:"
find output/issues -maxdepth 1 -name "*.ontology.issues.json" | wc -l

echo
echo "======================================"
echo "  DEMO CONCLUÍDA COM SUCESSO"
echo "======================================"