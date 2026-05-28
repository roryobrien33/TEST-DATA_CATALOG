#!/usr/bin/env python3
import glob
import sys
from pathlib import Path

import yaml


def die(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def load_yaml(fp: str) -> dict:
    p = Path(fp)
    if not p.exists():
        die(f"Missing YAML file: {fp}")
    try:
        with p.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        die(f"Failed to parse YAML {fp}: {e}")


def main() -> None:
    # Source of truth: issue-form generated catalogs
    files = sorted(glob.glob("data-catalog/user-catalogs/*.yaml")) + sorted(
        glob.glob("data-catalog/user-catalogs/*.yml")
    )

    # If there are no user catalogs yet, fail with a clear message
    # (You can change this to "generate empty merged file" if you prefer.)
    if not files:
        die("No user catalogs found. Expected at least one file matching data-catalog/user-catalogs/*.yaml (or *.yml).")

    catalogs = []
    for fp in files:
        doc = load_yaml(fp)
        if not isinstance(doc, dict) or "catalog" not in doc:
            die(f"{fp} must be a mapping with a top-level 'catalog' key.")
        catalogs.append(doc)

    merged = {"catalogs": catalogs}

    out = Path("data-catalog/data-catalog.yaml")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        yaml.safe_dump(merged, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )

    print(f"OK: merged {len(catalogs)} user catalogs into {out}")


if __name__ == "__main__":
    main()
