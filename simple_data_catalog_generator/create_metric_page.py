from pathlib import Path
import yaml

from rdflib import Graph, URIRef
from simple_data_catalog_generator.page_creation_functions import (
    write_file,
    get_id,
    get_title,
    get_prefLabel,
    get_definition,
)

def _datasets_for_metric(metric_id: str):
    rows = []

    catalog_files = sorted(Path("data-catalog/user-catalogs").glob("*.yaml")) + sorted(
        Path("data-catalog/user-catalogs").glob("*.yml")
    )

    for yf in catalog_files:
        doc = yaml.safe_load(yf.read_text(encoding="utf-8")) or {}
        datasets = doc.get("datasets", [])
        if not isinstance(datasets, list):
            continue

        for ds in datasets:
            if not isinstance(ds, dict):
                continue
            metric_ids = ds.get("metrics", [])
            if isinstance(metric_ids, str):
                metric_ids = [metric_ids]
            if not isinstance(metric_ids, list):
                continue

            if metric_id in [str(x).strip() for x in metric_ids]:
                ds_name = str(ds.get("title", "")).strip() or str(ds.get("id", "")).strip()
                ds_id = str(ds.get("id") or ds.get("identifier") or "").strip()
                rows.append((ds_name.lower(), ds_name, ds_id))

    rows.sort(key=lambda x: x[0])
    return rows


def _linked_datasets_table(metric_id: str) -> str:
    rows = _datasets_for_metric(metric_id)

    if not rows:
        return "No datasets linked to this metric.\n\n"

    table_str = "|===\n"
    table_str += "| Dataset | ID\n\n"

    for _, ds_name, ds_id in rows:
        table_str += f"| {ds_name}\n"
        table_str += f"| `{ds_id}`\n\n"

    table_str += "|===\n\n"
    return table_str


def create_metric_page(metric: URIRef, catalog_graph: Graph):
    adoc_str = str()

    metric_id = get_id(metric, catalog_graph)

    metric_name = get_prefLabel(metric, catalog_graph)
    if not metric_name or metric_name == "None":
        metric_name = get_title(metric, catalog_graph)
    if not metric_name or metric_name == "None":
        metric_name = metric_id

    metric_definition = get_definition(metric, catalog_graph)

    adoc_str += "= " + metric_name + "\n\n"

    adoc_str += "== Metric Details\n\n"
    adoc_str += f"* **Name:** {metric_name}\n"
    adoc_str += f"* **ID:** `{metric_id}`\n"

    if metric_definition and metric_definition != "None":
        adoc_str += f"* **Definition:** {metric_definition}\n"
    else:
        adoc_str += "* **Definition:** Not available\n"

    adoc_str += "\n"

    adoc_str += "== Linked datasets\n\n"
    adoc_str += _linked_datasets_table(metric_id)

    write_file(
        adoc_str=adoc_str,
        resource=metric,
        output_dir="modules/metric/pages/",
        catalog_graph=catalog_graph,
    )

    return 1
