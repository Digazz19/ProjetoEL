#!/bin/bash

set -e

echo "======================================"
echo "  DEMO ProjetoEL Communication Graph"
echo "======================================"

echo
echo "1. Gerar Layer 2 do exemplo de comunicação"
python3 main.py python examples/communication/communication_demo.launch.py

echo
echo "2. Pipeline de comunicação do exemplo controlado"
python3 scripts/run_communication_pipeline.py \
  output/communication_demo.launch.layer2.json \
  annotations/communication_demo.communication.yaml

echo
echo "3. Pipeline de comunicação do robot.launch"
python3 scripts/run_communication_pipeline.py \
  output/robot.launch.layer2.json \
  annotations/robot.communication.yaml

echo
echo "======================================"
echo "  DEMO COMMUNICATION CONCLUÍDA"
echo "======================================"