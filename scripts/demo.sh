#!/bin/bash

set -e

echo "== Testes Python =="
python3 test_launchfiles.py

echo
echo "== Exemplo XML =="
python3 main.py xml examples/example.launch.xml

echo
echo "== Exemplo YAML =="
python3 main.py yaml examples/example.launch.yaml