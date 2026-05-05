#!/bin/bash

set -e

echo "======================================"
echo "  1. Testes Layer 2 mínimos"
echo "======================================"
python3 test_layer2.py examples/layer2-minimal

echo
echo "======================================"
echo "  2. Testes de cobertura HAROS Layer 2"
echo "======================================"
python3 test_layer2.py examples/layer2-haros-coverage

echo
echo "======================================"
echo "  3. Exportação RDF/Turtle"
echo "======================================"
python3 scripts/export_all_layer2_to_rdf.py

echo
echo "======================================"
echo "  4. Validação SHACL"
echo "======================================"
python3 scripts/validate_all_rdf.py

echo
echo "======================================"
echo "  DEMO CONCLUÍDA COM SUCESSO"
echo "======================================"