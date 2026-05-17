#!/usr/bin/env python3

import sys
from rdflib import Graph
from pyshacl import validate


def main():
    if len(sys.argv) < 2:
        print("uso: python3 validate_rdf.py <ficheiro.ttl>")
        return 2

    rdf_file = sys.argv[1]
    shapes_file = "ontology/shapes.ttl"

    try:
        data_graph = Graph().parse(rdf_file, format="turtle")
    except Exception as e:
        print(f"[FAIL] erro ao ler RDF: {e}")
        return 1

    try:
        shapes_graph = Graph().parse(shapes_file, format="turtle")
    except Exception as e:
        print(f"[FAIL] erro ao ler SHACL shapes: {e}")
        return 1

    conforms, results_graph, results_text = validate(
        data_graph,
        shacl_graph=shapes_graph,
        inference="rdfs",
        debug=False
    )

    print(results_text)

    if conforms:
        print("\n[OK] RDF conforme às regras SHACL")
        return 0
    else:
        print("\n[FAIL] RDF não conforme")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())