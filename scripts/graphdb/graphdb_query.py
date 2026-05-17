#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path

import requests


def run_query(endpoint: str, query: str) -> dict:
    response = requests.post(
        endpoint,
        data={"query": query},
        headers={
            "Accept": "application/sparql-results+json",
        },
        timeout=60,
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Falha na query: {response.status_code} {response.text[:500]}"
        )

    return response.json()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Executa uma query SPARQL num repositório GraphDB."
    )
    parser.add_argument("query_file", help="Ficheiro .rq")
    parser.add_argument(
        "--base-url",
        default="http://localhost:7200",
    )
    parser.add_argument(
        "--repo",
        default="projetoel",
    )

    args = parser.parse_args()

    query_path = Path(args.query_file)

    query = query_path.read_text(encoding="utf-8")
    endpoint = f"{args.base_url.rstrip('/')}/repositories/{args.repo}"

    result = run_query(endpoint, query)

    vars_ = result.get("head", {}).get("vars", [])
    bindings = result.get("results", {}).get("bindings", [])

    print(f"[OK] Query: {query_path}")
    print(f"[OK] Resultados: {len(bindings)}")

    for row in bindings:
        values = []
        for var in vars_:
            val = row.get(var, {}).get("value", "")
            values.append(f"{var}={val}")
        print("  " + " | ".join(values))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())