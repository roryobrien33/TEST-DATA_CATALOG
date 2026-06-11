from pathlib import Path
import yaml

from rdflib import Graph, URIRef, DCAT, Namespace, RDF
from rdflib.namespace import DCTERMS
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
DQV = Namespace("http://www.w3.org/ns/dqv#")
ODRL = Namespace("http://www.w3.org/ns/odrl/2/")


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
    """
    Load the source dataset entry from the original user catalog YAML.

    This is needed because policies / metrics are currently stored in source YAML,
    not reliably round-tripped into the RDF graph for dataset page rendering.
    """
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

    # fallback: scan by catalog.id / catalog.title
    if source_file is None:
        catalog_files = sorted(Path("data-catalog/user-catalogs").glob("*.yaml")) + sorted(
            Path("data-catalog/user-catalogs").glob("*.yml")
        )

        for yf in catalog_files:
            doc = yaml.safe_load(yf.read_text(encoding="utf-8")) or {}
            cat = doc.get("catalog", {}) or {}

            cat_id = str(cat.get("id") or cat.get("identifier") or "").strip()
            cat_title = str(cat.get("title") or cat.get("name") or "").strip()

            if cat_id in candidate_names:
                source_file = yf
                break

            if series_title and cat_title == series_title:
                source_file = yf
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


def _find_policy_resource_by_identifier(catalog_graph: Graph, policy_identifier: str):
    for policy in catalog_graph.subjects(RDF.type, ODRL.Policy):
        pid = str(catalog_graph.value(policy, DCTERMS.identifier) or "").strip()
        if pid == policy_identifier:
            return policy

        # fallback for source-yaml-backed IDs
        policy_title = str(catalog_graph.value(policy, DCTERMS.title) or "").strip()
        if not pid and policy_title:
            # leave title match out intentionally to avoid false positives
            pass
    return None


def _find_metric_resource_by_identifier(catalog_graph: Graph, metric_identifier: str):
    for metric in catalog_graph.subjects(RDF.type, DQV.Metric):
        mid = str(catalog_graph.value(metric, DCTERMS.identifier) or "").strip()
        if mid == metric_identifier:
            return metric
    return None


def _id_links_table(ids, label_singular: str, catalog_graph: Graph, entity_type: str) -> str:
    if not ids:
        return f"No linked {label_singular.lower()}s.\n\n"

    rows = []

    for rid in ids:
        rid = str(rid).strip()
        if not rid:
            continue

        display_name = rid
        display_link = ""

        if entity_type == "policy":
            resource = _find_policy_resource_by_identifier(catalog_graph, rid)
            if resource is not None:
                display_name = get_title(resource, catalog_graph)
                display_link = create_local_link(resource, catalog_graph)

        elif entity_type == "metric":
            resource = _find_metric_resource_by_identifier(catalog_graph, rid)
            if resource is not None:
                display_name = get_prefLabel(resource, catalog_graph)
                if not display_name or display_name == "None":
                    display_name = get_title(resource, catalog_graph)
                display_link = create_local_link(resource, catalog_graph)

        rows.append(
            (
                display_name.lower(),
                display_link if display_link else display_name,
                rid,
            )
        )

    if not rows:
        return f"No linked {label_singular.lower()}s.\n\n"

    rows.sort(key=lambda x: x[0])

    table_str = "|===\n"
    table_str += f"| {label_singular} | ID\n\n"

    for _, name_display, rid in rows:
        table_str += f"| {name_display}\n"
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

    # Title
    adoc_str += "= " + dataset_name + "\n\n"

    # Dataset details
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

    # Description
    adoc_str += "== Description\n\n"
    if dataset_description and dataset_description != "None":
        adoc_str += dataset_description + "\n\n"
    else:
        adoc_str += "No description available.\n\n"

    # Themes / concepts
    adoc_str += "== Themes\n\n"
    adoc_str += _linked_concepts_table(dataset=dataset, catalog_graph=catalog_graph)

    # Policies
    adoc_str += "== Policies\n\n"
    adoc_str += _id_links_table(
        ids=policy_ids,
        label_singular="Policy",
        catalog_graph=catalog_graph,
        entity_type="policy",
    )

    # Metrics
    adoc_str += "== Metrics\n\n"
    adoc_str += _id_links_table(
        ids=metric_ids,
        label_singular="Metric",
        catalog_graph=catalog_graph,
        entity_type="metric",
    )

    # Distributions
    adoc_str += "== Distributions\n\n"
    if distributions:
        adoc_str += create_distribution_table(dataset=dataset, catalog_graph=catalog_graph)
        adoc_str += "\n\n"
    else:
        adoc_str += "No distributions available.\n\n"

    # Overview
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
