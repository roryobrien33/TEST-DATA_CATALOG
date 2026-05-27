#!/usr/bin/env python3
import glob
import sys
from pathlib import Path
import yaml

def die(msg: str):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)

def load_yaml(fp: str):
    p = Path(fp)
    try:
        return yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except Exception as e:
        die(f"Failed to parse YAML {fp}: {e}")

def main():
    files = sorted(glob.glob("catalogs/*.yaml"))
    if not files:
        die("No catalogs found. Expected at least one file matching catalogs/*.yaml")

    catalogs = []
    for fp in files:
        doc = load_yaml(fp)
        if not isinstance(doc, dict) or "catalog" not in doc:
            die(f"{fp} must be a dict with top-level key 'catalog'")
        catalogs.append(doc)

    # IMPORTANT: this output shape must match your LinkML schema.
    # We’ll start with the common pattern: top-level 'catalogs' list.
    merged = {"catalogs": catalogs}

    out = Path("data-catalog/data-catalog.yaml")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(yaml.safe_dump(merged, sort_keys=False, allow_unicode=True), encoding="utf-8")

    print(f"OK: merged {len(catalogs)} catalogs into {out}")

if __name__ == "__main__":
    main()
``
