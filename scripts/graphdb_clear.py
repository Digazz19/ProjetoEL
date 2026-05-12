#!/usr/bin/env python3

from __future__ import annotations

import argparse

import requests


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Remove todos os dados RDF de um repositório GraphDB."
    )
    parser.add_argument("--base-url", default="http://localhost:7200")
    parser.add_argument("--repo", default="projetoel")

    args = parser.parse_args()

    endpoint = f"{args.base_url.rstrip('/')}/repositories/{args.repo}/statements"

    response = requests.delete(endpoint, timeout=60)

    if response.status_code not in {200, 204}:
        raise RuntimeError(
            f"Falha ao limpar repositório: {response.status_code} {response.text[:500]}"
        )

    print(f"[OK] Repositório limpo: {args.repo}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())