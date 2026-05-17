#!/bin/bash

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

REPO=${1:-projetoel}

echo "======================================"
echo "  DEMO ProjetoEL GraphDB"
echo "  Repositório: $REPO"
echo "======================================"

echo
echo "1. Verificar RDFs locais"
if [ ! -d output/rdf ]; then
  echo "[ERRO] output/rdf não existe. Corre primeiro ./scripts/demos/demo.sh"
  exit 1
fi

echo
echo "2. Limpar repositório GraphDB"
python3 scripts/graphdb/graphdb_clear.py --repo "$REPO"

echo
echo "3. Upload de RDFs para GraphDB"
python3 scripts/graphdb/graphdb_upload.py output/rdf --repo "$REPO"

echo
echo "4. Query de teste"
python3 scripts/graphdb/graphdb_query.py ontology/queries/node_no_name.rq --repo "$REPO"

echo
echo "5. Gerar issues GraphDB"
python3 scripts/graphdb/run_graphdb_issues.py --repo "$REPO"

echo
echo "======================================"
echo "  DEMO GRAPHDB CONCLUÍDA"
echo "======================================"