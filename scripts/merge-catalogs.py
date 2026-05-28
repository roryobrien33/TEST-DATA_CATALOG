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


def first_present(d: dict, keys: list[str], default=None):
    for k in keys:
        if k in d and d[k] not in (None, ""):
            return d[k]
    return default


def ensure_curie(id_value: str, default_prefix: str = "sdcdc") -> str:
    """
    Ensure identifiers are CURIEs with a known prefix (or already URI/CURIE).
    - If the value already contains ':' -> keep it (e.g., ex:foo, sdcdc:bar, https://...).
    - Else -> prefix with default_prefix (e.g., sdcdc:XYZ).
    """
    s = (id_value or "").strip()
    if not s:
        return s
    if ":" in s:
        return s
    return f"{default_prefix}:{s}"


def normalize_dataset(ds: dict, source_catalog_id: str, idx: int) -> dict:
    """
    Map a user dataset entry to the LinkML Dataset shape (Resource.identifier required).
    Keep only schema-compatible fields: identifier/title/description for now.
    """
    raw_id = first_present(ds, ["identifier", "id"], None)
    if not raw_id:
        raw_id = f"DATASET-{source_catalog_id}-{idx:04d}"

    out = {"identifier": ensure_curie(str(raw_id))}

    title = first_present(ds, ["title", "name"], None)
    if title:
        out["title"] = str(title)

    desc = first_present(ds, ["description"], None)
    if desc:
        out["description"] = str(desc)

    # NOTE: Fields like use_case/location/concepts/distributions are not in your schema as-is.
    # We intentionally do not include them here to keep linkml-convert working.
    return out


def normalize_catalog(doc: dict, source_file: str) -> dict:
    """
    Map a user-catalog file to a LinkML DataCatalog instance:
    - identifier (required by Resource)
    - title/description optional
    - dataset: list[Dataset]
    """
    cat = doc.get("catalog", {})
    if cat is None:
        cat = {}
    if not isinstance(cat, dict):
        die(f"{source_file}: 'catalog' must be a mapping/object.")

    # user files typically have: catalog: { id, title, description, ... }
    raw_id = first_present(cat, ["identifier", "id"], None)
    if not raw_id:
        # fallback: use filename stem
        raw_id = f"CATALOG-{Path(source_file).stem}"

    catalog_id = ensure_curie(str(raw_id))

    out = {"identifier": catalog_id}

    title = first_present(cat, ["title", "name"], None)
    if title:
        out["title"] = str(title)

    desc = first_present(cat, ["description"], None)
    if desc:
        out["description"] = str(desc)

    # Build dataset list from top-level 'datasets' list in user file
    datasets = doc.get("datasets", [])
    if datasets is None:
        datasets = []
    if not isinstance(datasets, list):
        die(f"{source_file}: 'datasets' must be a list.")

    out_datasets = []
    for i, ds in enumerate(datasets, start=1):
        if not isinstance(ds, dict):
            die(f"{source_file}: dataset entry #{i} must be a mapping/object.")
        out_datasets.append(normalize_dataset(ds, source_catalog_id=Path(source_file).stem, idx=i))

    if out_datasets:
        out["dataset"] = out_datasets

    return out


def main() -> None:
    # Source of truth: issue-form generated catalogs
    files = sorted(glob.glob("data-catalog/user-catalogs/*.yaml")) + sorted(
        glob.glob("data-catalog/user-catalogs/*.yml")
    )

    if not files:
        die("No user catalogs found. Expected at least one file matching data-catalog/user-catalogs/*.yaml (or *.yml).")

    catalogs = []
    total_datasets = 0

    for fp in files:
        doc = load_yaml(fp)
        if not isinstance(doc, dict):
            die(f"{fp} must be a YAML mapping/object.")
        dc = normalize_catalog(doc, fp)
        # count datasets if present
        ds_list = dc.get("dataset", [])
        if isinstance(ds_list, list):
            total_datasets += len(ds_list)
        catalogs.append(dc)

    # NEW SCHEMA ROOT SHAPE:
    # Container.tree_root with required 'catalogs' slot (multivalued DataCatalog)
    merged = {"catalogs": catalogs}

    out = Path("data-catalog/data-catalog.yaml")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(yaml.safe_dump(merged, sort_keys=False, allow_unicode=True), encoding="utf-8")

    print(f"OK: merged {len(files)} user catalog file(s) and {total_datasets} dataset(s) into {out}")


if __name__ == "__main__":
    main()
