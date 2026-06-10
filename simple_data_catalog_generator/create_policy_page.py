from pathlib import Path
import yaml

from rdflib import Graph, URIRef
from simple_data_catalog_generator.page_creation_functions import (
    write_file,
    get_id,
    get_title,
    get_description,
)

def _datasets_for_policy(policy_id: str):
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
            policy_ids = ds.get("policies", [])
            if isinstance(policy_ids, str):
                policy_ids = [policy_ids]
            if not isinstance(policy_ids, list):
                continue

            if policy_id in [str(x).strip() for x in policy_ids]:
                ds_name = str(ds.get("title", "")).strip() or str(ds.get("id", "")).strip()
                ds_id = str(ds.get("id") or ds.get("identifier") or "").strip()
                rows.append((ds_name.lower(), ds_name, ds_id))

    rows.sort(key=lambda x: x[0])
    return rows


def _linked_datasets_table(policy_id: str) -> str:
    rows = _datasets_for_policy(policy_id)

    if not rows:
        return "No datasets linked to this policy.\n\n"

    table_str = "|===\n"
    table_str += "| Dataset | ID\n\n"

    for _, ds_name, ds_id in rows:
        table_str += f"| {ds_name}\n"
        table_str += f"| `{ds_id}`\n\n"

    table_str += "|===\n\n"
    return table_str


def create_policy_page(policy: URIRef, catalog_graph: Graph):
    adoc_str = str()

    policy_id = get_id(policy, catalog_graph)

    policy_title = get_title(policy, catalog_graph)
    if not policy_title or policy_title == "None":
        policy_title = policy_id

    policy_description = get_description(policy, catalog_graph)

    adoc_str += "= " + policy_title + "\n\n"

    adoc_str += "== Policy Details\n\n"
    adoc_str += f"* **Title:** {policy_title}\n"
    adoc_str += f"* **ID:** `{policy_id}`\n"

    if policy_description and policy_description != "None":
        adoc_str += f"* **Description:** {policy_description}\n"
    else:
        adoc_str += "* **Description:** Not available\n"

    adoc_str += "\n"

    adoc_str += "== Linked datasets\n\n"
    adoc_str += _linked_datasets_table(policy_id)

    write_file(
        adoc_str=adoc_str,
        resource=policy,
        output_dir="modules/policy/pages/",
        catalog_graph=catalog_graph,
    )

    return 1
