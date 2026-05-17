#!/bin/bash

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

echo "======================================"
echo "  DEMO ProjetoEL Communication Graph"
echo "======================================"

echo
echo "1. Gerar Layer 2 do exemplo de comunicação"
python3 main.py python examples/communication/communication_demo.launch.py

echo
echo "2. Gerar Layer 2 do robot.launch"
python3 main.py python examples/real-python/robot.launch.py

echo
echo "3. Pipeline de comunicação do exemplo controlado"
python3 scripts/communication/run_communication_pipeline.py \
  output/communication_demo.launch.layer2.json \
  node_interfaces/communication_demo.communication.yaml

echo
echo "4. Pipeline de comunicação do robot.launch"
python3 scripts/communication/run_communication_pipeline.py \
  output/robot.launch.layer2.json \
  node_interfaces/robot.communication.yaml

echo
echo "======================================"
echo "  DEMO COMMUNICATION CONCLUÍDA"
echo "======================================"