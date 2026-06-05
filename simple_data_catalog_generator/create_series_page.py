from pathlib import Path
import yaml

from rdflib import Graph, URIRef, DCAT
from simple_data_catalog_generator.page_creation_functions import (
    write_file,
    get_title,
    get_description,
    create_local_link,
    get_id,
)
from simple_data_catalog_generator.create_metadata_table import create_metadata_table


def _candidate_series_names(raw_id: str):
    """
    Given a series/catalog identifier, return possible source YAML base names
    that might correspond to the user-catalog file.

    Examples:
      sdcdc:A-SF0JMV -> ["sdcdc:A-SF0JMV", "A-SF0JMV"]
      https://.../A-SF0JMV -> ["https://.../A-SF0JMV", "A-SF0JMV"]
    """
    candidates = []

    if not raw_id:
        return candidates

    raw_id = str(raw_id).strip()
    candidates.append(raw_id)

    if ":" in raw_id:
        candidates.append(raw_id.split(":", 1)[1])

    if "/" in raw_id:
        candidates.append(raw_id.rstrip("/").split("/")[-1])

    if "#" in raw_id:
        candidates.append(raw_id.split("#")[-1])

    # de-duplicate while preserving order
    seen = set()
    cleaned = []
    for c in candidates:
        c = c.strip()
        if c and c not in seen:
            seen.add(c)
            cleaned.append(c)

    return cleaned


def _load_deleted_datasets_for_series(series: URIRef, catalog_graph: Graph):
    """
    Load deleted dataset tombstones from the source user-catalog YAML file
    that corresponds to this series/catalog.

    Expected source file patterns:
      data-catalog/user-catalogs/<series-id>.yaml
      data-catalog/user-catalogs/<series-id>.yml
    """
    raw_series_id = get_id(series, catalog_graph)
    candidate_names = _candidate_series_names(raw_series_id)

    source_file = None
    for name in candidate_names:
        for ext in (".yaml", ".yml"):
            candidate = Path(f"data-catalog/user-catalogs/{name}{ext}")
            if candidate.exists():
                source_file = candidate
                break
        if source_file is not None:
            break

    if source_file is None:
        print(f"WARNING: no source user-catalog YAML found for series id '{raw_series_id}'")
        return []

    doc = yaml.safe_load(source_file.read_text(encoding="utf-8")) or {}
    deleted_datasets = doc.get("deleted_datasets", [])

    if deleted_datasets is None:
        return []

    if not isinstance(deleted_datasets, list):
        return []

    cleaned = []
    for item in deleted_datasets:
        if isinstance(item, dict):
            cleaned.append(item)

    print(f"Loaded {len(cleaned)} deleted dataset tombstone(s) from {source_file}")
    return cleaned


def create_series_page(series: URIRef, catalog_graph: Graph):
    adoc_str = str()

    # ---------------------------
    # Load deleted dataset lineage info from source YAML
    # ---------------------------
    deleted_datasets = _load_deleted_datasets_for_series(series, catalog_graph)
    deleted_ids = {
        str(item.get("id", "")).strip()
        for item in deleted_datasets
        if str(item.get("id", "")).strip()
    }

    # ---------------------------
    # Title
    # ---------------------------
    adoc_str += "= " + get_title(series, catalog_graph) + "\n\n"

    # ---------------------------
    # Description
    # ---------------------------
    adoc_str += "== Description\n\n"
    desc = get_description(subject=series, graph=catalog_graph)
    if desc and desc != "None":
        adoc_str += desc + "\n\n"
    else:
        adoc_str += "No description available.\n\n"

    # ---------------------------
    # Themes
    # ---------------------------
    adoc_str += "== Themes\n\n"
    themes = [
        create_local_link(theme, catalog_graph)
        for theme in catalog_graph.objects(series, DCAT.theme)
    ]
    if themes:
        adoc_str += "\n".join(themes) + "\n\n"
    else:
        adoc_str += "No themes available.\n\n"

    # ---------------------------
    # Overview
    # ---------------------------
    adoc_str += "== Overview\n\n"
    adoc_str += create_metadata_table(
        catalog_graph=catalog_graph,
        resource=series
    )
    adoc_str += "\n\n"

    # ---------------------------
    # Active datasets in this series
    # ---------------------------
    adoc_str += "== Datasets in this series\n\n"

    active_dataset_links = []
    for dataset in catalog_graph.subjects(DCAT.inSeries, series):
        dataset_id = get_id(dataset, catalog_graph)

        # Do not show datasets that are recorded as deleted
        if dataset_id in deleted_ids:
          continue

        active_dataset_links.append(create_local_link(dataset, catalog_graph))

    if active_dataset_links:
        adoc_str += "\n".join(active_dataset_links) + "\n\n"
    else:
        adoc_str += "No active datasets in this series.\n\n"

    # ---------------------------
    # Deleted dataset lineage section
    # ---------------------------
    adoc_str += "== Deleted datasets in this series\n\n"

    if deleted_datasets:
        adoc_str += "|===\n"
        adoc_str += "| Name | ID | Deleted at | Description\n\n"

        for item in deleted_datasets:
            ds_id = str(item.get("id", "")).strip() or "Not available"
            ds_title = str(item.get("title", "")).strip() or "Not available"
            ds_deleted_at = str(item.get("deleted_at", "")).strip() or "Not available"
            ds_description = str(item.get("description", "")).strip() or "Not available"

            adoc_str += f"| {ds_title}\n"
            adoc_str += f"| `{ds_id}`\n"
            adoc_str += f"| {ds_deleted_at}\n"
            adoc_str += f"| {ds_description}\n\n"

        adoc_str += "|===\n\n"
    else:
        adoc_str += "No deleted datasets recorded for this series.\n\n"

    # ---------------------------
    # Write file
    # ---------------------------
    write_file(
        adoc_str=adoc_str,
        resource=series,
        output_dir='modules/dataset-series/pages/',
        catalog_graph=catalog_graph
    )

    return 1
