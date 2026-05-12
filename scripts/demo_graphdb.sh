#!/bin/bash

set -e

echo "======================================"
echo "  DEMO ProjetoEL GraphDB"
echo "======================================"

echo
echo "1. Verificar RDFs locais"
if [ ! -d output/rdf ]; then
  echo "[ERRO] output/rdf não existe. Corre primeiro ./scripts/demo.sh"
  exit 1
fi

echo
echo "2. Limpar repositório GraphDB"
python3 scripts/graphdb_clear.py --repo projetoel

echo
echo "3. Upload de RDFs para GraphDB"
python3 scripts/graphdb_upload.py output/rdf --repo projetoel

echo
echo "4. Query de teste"
python3 scripts/graphdb_query.py ontology/queries/node_no_name.rq --repo projetoel

echo
echo "5. Gerar issues GraphDB"
python3 scripts/run_graphdb_issues.py --repo projetoel

echo
echo "======================================"
echo "  DEMO GRAPHDB CONCLUÍDA"
echo "======================================"