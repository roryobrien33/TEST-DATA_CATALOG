#!/usr/bin/env python3
import glob
import re
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


def slugify(value: str) -> str:
    s = str(value).strip().lower()
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"[^a-z0-9-]", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s


def ensure_curie(value: str, default_prefix: str = "sdcdc") -> str:
    s = (value or "").strip()
    if not s:
        return s
    if s.startswith("http://") or s.startswith("https://"):
        return s
    if ":" in s:
        return s
    return f"{default_prefix}:{s}"


def extract_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str):
        return [v.strip() for v in value.split(",") if v.strip()]
    return []


def concept_id_from_label(label: str) -> str:
    return ensure_curie(f"concept-{slugify(label)}")


def build_series_from_catalog(cat: dict, source_stem: str) -> dict:
    raw_id = first_present(cat, ["identifier", "id"], None)
    if not raw_id:
        raw_id = f"series-{source_stem}"

    out = {"identifier": ensure_curie(str(raw_id))}

    title = first_present(cat, ["title", "name"], None)
    if title:
        out["title"] = str(title)
    else:
        out["title"] = source_stem

    desc = first_present(cat, ["description"], None)
    if desc:
        out["description"] = str(desc)

    publisher = cat.get("publisher")
    if isinstance(publisher, dict):
        name = first_present(publisher, ["name"], None)
        if name:
            out["publisher"] = {"name": str(name)}
    elif isinstance(publisher, str) and publisher.strip():
        out["publisher"] = {"name": publisher.strip()}

    return out


def normalize_dataset(
    ds: dict,
    source_catalog_stem: str,
    idx: int,
    series_id: str,
    concepts_map: dict,
) -> dict:
    raw_id = first_present(ds, ["identifier", "id"], None)
    if not raw_id:
        raw_id = f"dataset-{source_catalog_stem}-{idx:04d}"

    dataset_id = ensure_curie(str(raw_id))
    out = {"identifier": dataset_id}

    title = first_present(ds, ["title", "name"], None)
    if title:
        # Make dataset ID visible in the rendered page
        out["title"] = f"{str(title)} [ID: {dataset_id}]"
    else:
        out["title"] = f"[ID: {dataset_id}]"

    desc = first_present(ds, ["description"], None)
    if desc:
        out["description"] = str(desc)

    # Preserve source catalog separation inside the merged catalog
    out["inSeries"] = series_id

    publisher = ds.get("publisher")
    if isinstance(publisher, dict):
        name = first_present(publisher, ["name"], None)
        if name:
            out["publisher"] = {"name": str(name)}
    elif isinstance(publisher, str) and publisher.strip():
        out["publisher"] = {"name": publisher.strip()}

    # Map concepts/tags/theme into schema-supported theme + top-level concepts
    labels = []
    labels += extract_list(ds.get("concepts"))
    labels += extract_list(ds.get("tags"))

    theme_val = ds.get("theme")
    if isinstance(theme_val, list):
        for item in theme_val:
            if isinstance(item, str) and item.strip():
                labels.append(item.strip())
            elif isinstance(item, dict):
                lbl = first_present(item, ["prefLabel", "label", "title", "name"], None)
                cid = first_present(item, ["identifier", "id"], None)
                if cid:
                    cid = ensure_curie(str(cid))
                    concepts_map[cid] = {
                        "identifier": cid,
                        "prefLabel": lbl or str(cid),
                    }
                    labels.append(lbl or str(cid))
                elif lbl:
                    labels.append(lbl)
    elif isinstance(theme_val, str) and theme_val.strip():
        labels.append(theme_val.strip())

    seen = set()
    ordered_labels = []
    for lbl in labels:
        key = lbl.strip().lower()
        if key and key not in seen:
            seen.add(key)
            ordered_labels.append(lbl.strip())

    if ordered_labels:
        theme_ids = []
        for lbl in ordered_labels:
            cid = concept_id_from_label(lbl)
            theme_ids.append(cid)
            if cid not in concepts_map:
                concepts_map[cid] = {
                    "identifier": cid,
                    "prefLabel": lbl,
                }
        out["theme"] = theme_ids

    return out


def main() -> None:
    files = sorted(glob.glob("data-catalog/user-catalogs/*.yaml")) + sorted(
        glob.glob("data-catalog/user-catalogs/*.yml")
    )

    if not files:
        die("No user catalogs found. Expected at least one file matching data-catalog/user-catalogs/*.yaml (or *.yml).")

    all_datasets = []
    all_series = []
    concepts_map = {}

    for fp in files:
        doc = load_yaml(fp)
        if not isinstance(doc, dict):
            die(f"{fp} must be a YAML mapping/object.")

        cat = doc.get("catalog", {})
        if cat is None:
            cat = {}
        if not isinstance(cat, dict):
            die(f"{fp}: 'catalog' must be a mapping/object.")

        source_stem = Path(fp).stem
        series_obj = build_series_from_catalog(cat, source_stem)
        series_id = series_obj["identifier"]
        all_series.append(series_obj)

        datasets = doc.get("datasets", [])
        if datasets is None:
            datasets = []
        if not isinstance(datasets, list):
            die(f"{fp}: 'datasets' must be a list.")

        for i, ds in enumerate(datasets, start=1):
            if not isinstance(ds, dict):
                die(f"{fp}: dataset entry #{i} must be a mapping/object.")
            all_datasets.append(
                normalize_dataset(
                    ds=ds,
                    source_catalog_stem=source_stem,
                    idx=i,
                    series_id=series_id,
                    concepts_map=concepts_map,
                )
            )

    dataset_refs = [ds["identifier"] for ds in all_datasets]

    container = {
        "dataCatalog": {
            "identifier": "sdcdc:USER-CATALOG",
            "title": "User Catalog",
            "description": "Aggregated datasets from data-catalog/user-catalogs/",
        },
        "datasets": all_datasets,
        "series": all_series,
    }

    if dataset_refs:
        container["dataCatalog"]["dataset"] = dataset_refs

    if concepts_map:
        container["concepts"] = sorted(
            concepts_map.values(),
            key=lambda x: x.get("prefLabel", "").lower()
        )

    out = Path("data-catalog/data-catalog.yaml")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        yaml.safe_dump(container, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )

    print(f"OK: merged {len(files)} user catalog file(s) and {len(all_datasets)} dataset(s) into {out}")


if __name__ == "__main__":
    main()
``
