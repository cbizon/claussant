#!/usr/bin/env python3
"""
Croissant provenance cross-check.

Usage:
    python3 references/check_provenance.py <name>_croissant.json <name>_provenance.json

Exits 0 if every croissant_id leaf key in the provenance file appears in the
Croissant file. Exits 1 and prints mismatches otherwise.
"""
import json, sys


def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <croissant.json> <provenance.json>")
        sys.exit(2)

    croissant_path, provenance_path = sys.argv[1], sys.argv[2]

    with open(croissant_path) as f:
        croissant_text = f.read()
    with open(provenance_path) as f:
        prov = json.load(f)

    errors = []
    for claim in prov.get("claims", []):
        cid = claim.get("croissant_id", "")
        leaf = cid.split("/")[-1]
        if leaf and f'"{leaf}"' not in croissant_text:
            errors.append(f"  croissant_id {cid!r} — leaf key {leaf!r} not found in Croissant file")

    if errors:
        print("PROVENANCE MISMATCH — fix these before delivering:")
        print("\n".join(errors))
        sys.exit(1)
    else:
        print("OK — all croissant_id leaf keys found in Croissant file")


if __name__ == "__main__":
    main()
