#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path

import requests


def collect_ttl_files(input_path: Path) -> list[Path]:
    """
    Recolhe ficheiros Turtle.

    Se input_path for ficheiro, carrega só esse ficheiro.
    Se for pasta, procura recursivamente por *.ttl, incluindo subpastas
    como output/rdf/architecture/.
    """
    if input_path.is_file():
        if input_path.suffix != ".ttl":
            return []
        return [input_path]

    return sorted(input_path.rglob("*.ttl"))


def upload_ttl(endpoint: str, ttl_path: Path, graph_uri: str | None = None) -> None:
    params = {}

    if graph_uri:
        params["context"] = f"<{graph_uri}>"

    with ttl_path.open("rb") as f:
        response = requests.post(
            endpoint,
            params=params,
            data=f,
            headers={
                "Content-Type": "text/turtle",
            },
            timeout=60,
        )

    if response.status_code not in {200, 201, 204}:
        raise RuntimeError(
            f"Falha no upload de {ttl_path}: "
            f"{response.status_code} {response.text[:500]}"
        )


def graph_uri_for_file(ttl_path: Path) -> str:
    """
    URI estável para named graph, caso --named-graphs seja usado.
    Inclui o path relativo normalizado para evitar colisões entre ficheiros
    com o mesmo nome em pastas diferentes.
    """
    safe_name = str(ttl_path).replace("/", "__").replace("\\", "__")
    return f"http://example.org/ros-launch/graph/{safe_name}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Carrega ficheiros Turtle para um repositório GraphDB."
    )
    parser.add_argument(
        "path",
        help="Ficheiro .ttl ou pasta com ficheiros .ttl",
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:7200",
        help="URL base do GraphDB",
    )
    parser.add_argument(
        "--repo",
        default="projetoel",
        help="ID do repositório GraphDB",
    )
    parser.add_argument(
        "--named-graphs",
        action="store_true",
        help="Carregar cada ficheiro para um named graph próprio",
    )

    args = parser.parse_args()

    input_path = Path(args.path)

    if not input_path.exists():
        raise FileNotFoundError(input_path)

    endpoint = f"{args.base_url.rstrip('/')}/repositories/{args.repo}/statements"
    ttl_files = collect_ttl_files(input_path)

    if not ttl_files:
        print(f"[AVISO] Nenhum .ttl encontrado em {input_path}")
        return 0

    for ttl in ttl_files:
        graph_uri = None

        if args.named_graphs:
            graph_uri = graph_uri_for_file(ttl)

        print(f"[UPLOAD] {ttl}")
        upload_ttl(endpoint, ttl, graph_uri=graph_uri)

    print(f"[OK] Ficheiros carregados: {len(ttl_files)}")
    print(f"[OK] Repositório: {args.repo}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())