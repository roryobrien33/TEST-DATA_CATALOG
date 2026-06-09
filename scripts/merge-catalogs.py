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


def load_independent_concepts() -> dict:
    """
    Load independent concept definitions from:
      data-catalog/concepts/*.yaml
      data-catalog/concepts/*.yml

    Note:
    - broader/narrower are intentionally kept in source YAML and rendered
      from source later, because the current schema does not formally define them.
    """
    concept_files = sorted(glob.glob("data-catalog/concepts/*.yaml")) + sorted(
        glob.glob("data-catalog/concepts/*.yml")
    )

    concepts_map = {}
    label_to_id = {}

    for fp in concept_files:
        doc = load_yaml(fp)
        if not isinstance(doc, dict):
            die(f"{fp} must be a YAML mapping/object.")

        concept = doc.get("concept", {})
        if concept is None:
            concept = {}
        if not isinstance(concept, dict):
            die(f"{fp}: 'concept' must be a mapping/object.")

        raw_id = first_present(concept, ["identifier", "id"], None)
        if not raw_id:
            raw_id = f"concept-{Path(fp).stem}"

        cid = ensure_curie(str(raw_id))
        pref_label = first_present(concept, ["prefLabel", "label", "title", "name"], None)
        definition = first_present(concept, ["definition"], None)
        alt_label = first_present(concept, ["altLabel"], None)
        example = first_present(concept, ["example"], None)

        concept_obj = {
            "identifier": cid,
        }

        if pref_label:
            concept_obj["prefLabel"] = str(pref_label)
            label_to_id[str(pref_label).strip().lower()] = cid

        if definition:
            concept_obj["definition"] = str(definition)

        if alt_label:
            concept_obj["altLabel"] = str(alt_label)

        if example:
            concept_obj["example"] = str(example)

        concepts_map[cid] = concept_obj

    return {"concepts_map": concepts_map, "label_to_id": label_to_id}


def load_independent_metrics() -> dict:
    """
    Load independent metric definitions from:
      data-catalog/metrics/*.yaml
      data-catalog/metrics/*.yml
    """
    metric_files = sorted(glob.glob("data-catalog/metrics/*.yaml")) + sorted(
        glob.glob("data-catalog/metrics/*.yml")
    )

    metrics_map = {}

    for fp in metric_files:
        doc = load_yaml(fp)
        if not isinstance(doc, dict):
            die(f"{fp} must be a YAML mapping/object.")

        metric = doc.get("metric", {})
        if metric is None:
            metric = {}
        if not isinstance(metric, dict):
            die(f"{fp}: 'metric' must be a mapping/object.")

        raw_id = first_present(metric, ["identifier", "id"], None)
        if not raw_id:
            raw_id = f"metric-{Path(fp).stem}"

        mid = ensure_curie(str(raw_id))
        pref_label = first_present(metric, ["prefLabel", "label", "title", "name"], None)
        definition = first_present(metric, ["definition"], None)
        expected_data_type = first_present(metric, ["expectedDataType"], None)
        in_dimension = first_present(metric, ["inDimension", "dimension"], None)

        metric_obj = {
            "identifier": mid,
        }

        if pref_label:
            metric_obj["prefLabel"] = str(pref_label)

        if definition:
            metric_obj["definition"] = str(definition)

        if expected_data_type:
            metric_obj["expectedDataType"] = str(expected_data_type)

        if in_dimension:
            metric_obj["inDimension"] = str(in_dimension)

        metrics_map[mid] = metric_obj

    return {"metrics_map": metrics_map}


def load_independent_policies() -> dict:
    """
    Load independent policy definitions from:
      data-catalog/policies/*.yaml
      data-catalog/policies/*.yml

    Expected shape:
      policy:
        uid: plcy:open-information
        title: Open Information Policy
        description: ...
    """
    policy_files = sorted(glob.glob("data-catalog/policies/*.yaml")) + sorted(
        glob.glob("data-catalog/policies/*.yml")
    )

    policies_map = {}

    for fp in policy_files:
        doc = load_yaml(fp)
        if not isinstance(doc, dict):
            die(f"{fp} must be a YAML mapping/object.")

        policy = doc.get("policy", {})
        if policy is None:
            policy = {}
        if not isinstance(policy, dict):
            die(f"{fp}: 'policy' must be a mapping/object.")

        raw_id = first_present(policy, ["uid", "identifier", "id"], None)
        if not raw_id:
            raw_id = f"policy-{Path(fp).stem}"

        pid = ensure_curie(str(raw_id), default_prefix="plcy")
        title = first_present(policy, ["title", "name"], None)
        description = first_present(policy, ["description"], None)

        policy_obj = {
            "uid": pid,
        }

        if title:
            policy_obj["title"] = str(title)

        if description:
            policy_obj["description"] = str(description)

        policies_map[pid] = policy_obj

    return {"policies_map": policies_map}


def normalize_dataset(
    ds: dict,
    source_catalog_stem: str,
    idx: int,
    series_id: str,
    concepts_map: dict,
    label_to_id: dict,
) -> dict:
    raw_id = first_present(ds, ["identifier", "id"], None)
    if not raw_id:
        raw_id = f"dataset-{source_catalog_stem}-{idx:04d}"

    dataset_id = ensure_curie(str(raw_id))
    out = {"identifier": dataset_id}

    title = first_present(ds, ["title", "name"], None)
    if title:
        out["title"] = f"{str(title)} [ID: {dataset_id}]"
    else:
        out["title"] = f"[ID: {dataset_id}]"

    desc = first_present(ds, ["description"], None)
    if desc:
        out["description"] = str(desc)

    # Preserve source catalog separation inside merged catalog
    out["inSeries"] = series_id

    publisher = ds.get("publisher")
    if isinstance(publisher, dict):
        name = first_present(publisher, ["name"], None)
        if name:
            out["publisher"] = {"name": str(name)}
    elif isinstance(publisher, str) and publisher.strip():
        out["publisher"] = {"name": publisher.strip()}

    # Concepts / themes
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
                    labels.append(cid)
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
            # explicit CURIE / IRI
            if lbl.startswith("http://") or lbl.startswith("https://") or ":" in lbl:
                cid = ensure_curie(lbl)
                theme_ids.append(cid)

                if cid not in concepts_map:
                    concepts_map[cid] = {
                        "identifier": cid,
                        "prefLabel": lbl,
                    }
                continue

            # match by label
            matched_cid = label_to_id.get(lbl.strip().lower())
            if matched_cid:
                theme_ids.append(matched_cid)
                continue

            # fallback auto concept from label
            cid = concept_id_from_label(lbl)
            theme_ids.append(cid)
            if cid not in concepts_map:
                concepts_map[cid] = {
                    "identifier": cid,
                    "prefLabel": lbl,
                }

        out["theme"] = theme_ids

    # Policy linkage (optional)
    has_policy = first_present(ds, ["hasPolicy"], None)
    if has_policy:
        out["hasPolicy"] = ensure_curie(str(has_policy), default_prefix="plcy")

    return out


def main() -> None:
    files = sorted(glob.glob("data-catalog/user-catalogs/*.yaml")) + sorted(
        glob.glob("data-catalog/user-catalogs/*.yml")
    )

    if not files:
        die("No user catalogs found. Expected at least one file matching data-catalog/user-catalogs/*.yaml (or *.yml).")

    all_datasets = []
    all_series = []

    loaded_concepts = load_independent_concepts()
    concepts_map = loaded_concepts["concepts_map"]
    label_to_id = loaded_concepts["label_to_id"]

    loaded_metrics = load_independent_metrics()
    metrics_map = loaded_metrics["metrics_map"]

    loaded_policies = load_independent_policies()
    policies_map = loaded_policies["policies_map"]

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
                    label_to_id=label_to_id,
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

    if metrics_map:
        container["metrics"] = sorted(
            metrics_map.values(),
            key=lambda x: x.get("prefLabel", "").lower()
        )

    if policies_map:
        container["policies"] = sorted(
            policies_map.values(),
            key=lambda x: x.get("title", "").lower()
        )

    out = Path("data-catalog/data-catalog.yaml")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        yaml.safe_dump(container, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )

    print(
        f"OK: merged {len(files)} user catalog file(s), "
        f"{len(all_datasets)} dataset(s), "
        f"{len(concepts_map)} concept(s), "
        f"{len(metrics_map)} metric(s), and "
        f"{len(policies_map)} policy/policies into {out}"
    )


if __name__ == "__main__":
    main()
