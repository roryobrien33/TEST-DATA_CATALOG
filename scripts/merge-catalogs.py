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


def normalize_dataset(doc: dict, source_file: str, idx: int) -> dict:
    """
    Convert a user-catalog dataset entry into a LinkML Dataset instance
    that satisfies Resource.identifier (required).
    We keep only fields that exist in your schema: identifier/title/description.
    """
    ds_id = first_present(doc, ["identifier", "id"], None)
    if not ds_id:
        # guarantee identifier so linkml runtime doesn't fail
        ds_id = f"DATASET-{Path(source_file).stem}-{idx:04d}"

    out = {"identifier": str(ds_id)}

    title = first_present(doc, ["title", "name"], None)
    if title:
        out["title"] = str(title)

    desc = first_present(doc, ["description"], None)
    if desc:
        out["description"] = str(desc)

    # NOTE: user fields like use_case/location/concepts/distributions are not in your schema as-is.
    # We intentionally ignore them here to keep linkml-convert working.
    return out


def main() -> None:
    # Source of truth: issue-form generated catalogs
    files = sorted(glob.glob("data-catalog/user-catalogs/*.yaml")) + sorted(
        glob.glob("data-catalog/user-catalogs/*.yml")
    )

    if not files:
        die("No user catalogs found. Expected at least one file matching data-catalog/user-catalogs/*.yaml (or *.yml).")

    all_datasets: list[dict] = []

    for fp in files:
        doc = load_yaml(fp)
        if not isinstance(doc, dict):
            die(f"{fp} must be a YAML mapping/object.")

        # Your user-catalog files currently look like:
        #   catalog: {...}
        #   datasets: [ ... ]
        datasets = doc.get("datasets", [])
        if datasets is None:
            datasets = []
        if not isinstance(datasets, list):
            die(f"{fp}: 'datasets' must be a list.")

        for i, ds in enumerate(datasets, start=1):
            if not isinstance(ds, dict):
                die(f"{fp}: dataset entry #{i} must be a mapping/object.")
            all_datasets.append(normalize_dataset(ds, fp, i))

    # Build a schema-valid Container instance.
    # Container requires: dataCatalog (required: true in schema)
    # DataCatalog is a Dataset -> Resource, so it MUST have identifier.
    container = {
        "dataCatalog": {
            "identifier": "USER-CATALOG",
            "title": "User Catalog",
            "description": "Aggregated datasets from data-catalog/user-catalogs/",
            "dataset": all_datasets,  # link to datasets from the catalog
        },
        "datasets": all_datasets,  # also provide datasets at container level (schema supports this)
    }

    out = Path("data-catalog/data-catalog.yaml")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        yaml.safe_dump(container, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )

    print(f"OK: merged {len(files)} user catalog file(s) and {len(all_datasets)} dataset(s) into {out}")


if __name__ == "__main__":
    main()
