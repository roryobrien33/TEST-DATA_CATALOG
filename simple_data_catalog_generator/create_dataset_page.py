from pathlib import Path
import yaml

from rdflib import Graph, URIRef, DCAT, Namespace
from simple_data_catalog_generator.page_creation_functions import (
    write_file,
    get_title,
    get_description,
    create_local_link,
    get_id,
    get_prefLabel,
)
from simple_data_catalog_generator.create_distribution_table import create_distribution_table

SDCDC = Namespace("https://www.uuidea.eu/profiles/data-catalog/")


def _first_literal(graph: Graph, subject: URIRef, predicates):
    for pred in predicates:
        val = graph.value(subject, pred)
        if val is not None and str(val).strip() and str(val).strip() != "None":
            return str(val).strip()
    return ""


def _candidate_catalog_names(raw_id: str, title: str):
    candidates = []

    if raw_id:
        raw_id = str(raw_id).strip()
        candidates.append(raw_id)

        if ":" in raw_id:
            candidates.append(raw_id.split(":", 1)[1])

        if "/" in raw_id:
            candidates.append(raw_id.rstrip("/").split("/")[-1])

        if "#" in raw_id:
            candidates.append(raw_id.split("#")[-1])

    if title:
        candidates.append(str(title).strip())

    seen = set()
    cleaned = []
    for c in candidates:
        c = c.strip()
        if c and c not in seen:
            seen.add(c)
            cleaned.append(c)

    return cleaned


def _load_source_dataset_yaml(dataset: URIRef, catalog_graph: Graph):
    linked_series = catalog_graph.value(dataset, DCAT.inSeries)
    if linked_series is None:
        return {}

    raw_series_id = get_id(linked_series, catalog_graph)
    series_title = get_title(linked_series, catalog_graph)
    candidate_names = _candidate_catalog_names(raw_series_id, series_title)

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
        return {}

    doc = yaml.safe_load(source_file.read_text(encoding="utf-8")) or {}
    datasets = doc.get("datasets", [])
    if not isinstance(datasets, list):
        return {}

    dataset_id = get_id(dataset, catalog_graph)

    for ds in datasets:
        if not isinstance(ds, dict):
            continue
        ds_id = str(ds.get("id") or ds.get("identifier") or "").strip()
        if ds_id == dataset_id:
            return ds

    return {}


def _linked_concepts_table(dataset: URIRef, catalog_graph: Graph) -> str:
    rows = []

    for concept in catalog_graph.objects(dataset, DCAT.theme):
        concept_name = get_prefLabel(concept, catalog_graph)
        if not concept_name or concept_name == "None":
            concept_name = get_title(concept, catalog_graph)
        if not concept_name or concept_name == "None":
            concept_name = get_id(concept, catalog_graph)

        concept_id = get_id(concept, catalog_graph)
        concept_link = create_local_link(concept, catalog_graph)
        concept_name_display = concept_link if concept_link else concept_name

        rows.append((concept_name.lower(), concept_name_display, concept_id))

    if not rows:
        return "No linked concepts.\n\n"

    rows.sort(key=lambda x: x[0])

    table_str = "|===\n"
    table_str += "| Concept | ID\n\n"

    for _, concept_name_display, concept_id in rows:
        table_str += f"| {concept_name_display}\n"
        table_str += f"| `{concept_id}`\n\n"

    table_str += "|===\n\n"
    return table_str


def _simple_id_table(ids, label_singular: str) -> str:
    if not ids:
        return f"No linked {label_singular.lower()}s.\n\n"

    rows = sorted([str(x).strip() for x in ids if str(x).strip()], key=lambda x: x.lower())

    table_str = "|===\n"
    table_str += f"| {label_singular} ID\n\n"

    for rid in rows:
        table_str += f"| `{rid}`\n\n"

    table_str += "|===\n\n"
    return table_str


def create_dataset_page(dataset: URIRef, catalog_graph: Graph):
    adoc_str = str()

    dataset_name = get_title(dataset, catalog_graph)
    dataset_id = get_id(dataset, catalog_graph)
    dataset_description = get_description(subject=dataset, graph=catalog_graph)

    linked_series = catalog_graph.value(dataset, DCAT.inSeries)
    linked_catalog_id = ""
    linked_catalog_link = ""
    if linked_series is not None:
        linked_catalog_id = get_id(linked_series, catalog_graph)
        linked_catalog_link = create_local_link(linked_series, catalog_graph)

    dataset_use_case = _first_literal(
        catalog_graph,
        dataset,
        [
            SDCDC.use_case,
            SDCDC.useCase,
            Namespace("https://www.uuidea.eu/profiles/data-catalog/")["use_case"],
            Namespace("https://www.uuidea.eu/profiles/data-catalog/")["useCase"],
        ],
    )

    distributions = list(catalog_graph.objects(dataset, DCAT.distribution))
    source_dataset = _load_source_dataset_yaml(dataset, catalog_graph)

    policy_ids = source_dataset.get("policies", [])
    if isinstance(policy_ids, str):
        policy_ids = [policy_ids]
    if not isinstance(policy_ids, list):
        policy_ids = []

    metric_ids = source_dataset.get("metrics", [])
    if isinstance(metric_ids, str):
        metric_ids = [metric_ids]
    if not isinstance(metric_ids, list):
        metric_ids = []

    adoc_str += "= " + dataset_name + "\n\n"

    adoc_str += "== Dataset Details\n\n"
    adoc_str += f"* **Name:** {dataset_name}\n"
    adoc_str += f"* **ID:** `{dataset_id}`\n"

    if linked_catalog_link:
        adoc_str += f"* **Linked Catalog ID:** `{linked_catalog_id}` ({linked_catalog_link})\n"
    elif linked_catalog_id:
        adoc_str += f"* **Linked Catalog ID:** `{linked_catalog_id}`\n"
    else:
        adoc_str += "* **Linked Catalog ID:** Not available\n"

    if dataset_description and dataset_description != "None":
        adoc_str += f"* **Description:** {dataset_description}\n"
    else:
        adoc_str += "* **Description:** Not available\n"

    if dataset_use_case:
        adoc_str += f"* **Use case:** {dataset_use_case}\n"
    else:
        adoc_str += "* **Use case:** Not available\n"

    if distributions:
        adoc_str += f"* **Distributions:** {len(distributions)} available (see section below)\n"
    else:
        adoc_str += "* **Distributions:** None\n"

    adoc_str += "\n"

    adoc_str += "== Description\n\n"
    if dataset_description and dataset_description != "None":
        adoc_str += dataset_description + "\n\n"
    else:
        adoc_str += "No description available.\n\n"

    adoc_str += "== Themes\n\n"
    adoc_str += _linked_concepts_table(dataset=dataset, catalog_graph=catalog_graph)

    adoc_str += "== Policies\n\n"
    adoc_str += _simple_id_table(policy_ids, "Policy")

    adoc_str += "== Metrics\n\n"
    adoc_str += _simple_id_table(metric_ids, "Metric")

    adoc_str += "== Distributions\n\n"
    if distributions:
        adoc_str += create_distribution_table(dataset=dataset, catalog_graph=catalog_graph)
        adoc_str += "\n\n"
    else:
        adoc_str += "No distributions available.\n\n"

    adoc_str += "== Overview\n\n"
    adoc_str += (
        f"|===\n"
        f"|Field |Value\n\n"
        f"|Name |{dataset_name}\n"
        f"|ID |`{dataset_id}`\n"
        f"|Linked Catalog ID |{linked_catalog_id if linked_catalog_id else 'Not available'}\n"
        f"|Use case |{dataset_use_case if dataset_use_case else 'Not available'}\n"
        f"|===\n\n"
    )

    write_file(
        adoc_str=adoc_str,
        resource=dataset,
        output_dir="modules/dataset/pages/",
        catalog_graph=catalog_graph,
    )

    return 1
