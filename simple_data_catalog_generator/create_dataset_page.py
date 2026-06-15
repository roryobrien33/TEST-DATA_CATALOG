from pathlib import Path
import re
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

SDCDC = Namespace("https://www.uuidea.eu/profiles/data-catalog/")
DQV = Namespace("http://www.w3.org/ns/dqv#")
ODRL = Namespace("http://www.w3.org/ns/odrl/2/")


def _first_literal(graph: Graph, subject: URIRef, predicates):
    for pred in predicates:
        val = graph.value(subject, pred)
        if val is not None and str(val).strip() and str(val).strip() != "None":
            return str(val).strip()
    return ""


def _dataset_id_candidates(dataset: URIRef, catalog_graph: Graph) -> list[str]:
    """
    Build a robust list of candidate identifiers for this dataset so we can
    match it back to the source YAML entry even if the RDF layer stores or
    exposes the identifier slightly differently.
    """
    candidates = []

    dataset_id = str(get_id(dataset, catalog_graph) or "").strip()
    if dataset_id:
        candidates.append(dataset_id)

        if ":" in dataset_id:
            candidates.append(dataset_id.split(":", 1)[1])

        if "/" in dataset_id:
            candidates.append(dataset_id.rstrip("/").split("/")[-1])

        if "#" in dataset_id:
            candidates.append(dataset_id.split("#")[-1])

        if dataset_id.startswith("data-catalog"):
            candidates.append(dataset_id.replace("data-catalog", "", 1).lstrip("-_/"))

    dataset_uri = str(dataset).strip()
    if dataset_uri:
        candidates.append(dataset_uri)

        if "/" in dataset_uri:
            candidates.append(dataset_uri.rstrip("/").split("/")[-1])

        if "#" in dataset_uri:
            candidates.append(dataset_uri.split("#")[-1])

    dataset_title = str(get_title(dataset, catalog_graph) or "").strip()
    if dataset_title:
        candidates.append(dataset_title)

        # Extract embedded [ID: ...] if present in title
        m = re.search(r"\[ID:\s*([^\]]+)\]", dataset_title)
        if m:
            embedded_id = m.group(1).strip()
            candidates.append(embedded_id)

            if ":" in embedded_id:
                candidates.append(embedded_id.split(":", 1)[1])

    seen = set()
    cleaned = []
    for c in candidates:
        c = str(c).strip()
        if c and c not in seen:
            seen.add(c)
            cleaned.append(c)

    return cleaned


def _load_source_dataset_yaml(dataset: URIRef, catalog_graph: Graph):
    """
    Load the source dataset entry from any original user catalog YAML by matching
    a robust set of candidate IDs against the dataset entries.
    """
    candidate_ids = _dataset_id_candidates(dataset, catalog_graph)

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

            ds_id = str(ds.get("id") or ds.get("identifier") or "").strip()
            ds_title = str(ds.get("title") or "").strip()

            ds_candidates = [ds_id, ds_title]
            if ds_id:
                if ":" in ds_id:
                    ds_candidates.append(ds_id.split(":", 1)[1])
                if "/" in ds_id:
                    ds_candidates.append(ds_id.rstrip("/").split("/")[-1])
                if "#" in ds_id:
                    ds_candidates.append(ds_id.split("#")[-1])

            matched = False
            for cand in candidate_ids:
                if cand and cand in ds_candidates:
                    matched = True
                    break

            if matched:
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
                if not display_name or display_name == "None":
                    display_name = rid
                display_link = create_local_link(resource, catalog_graph)

        elif entity_type == "metric":
            resource = _find_metric_resource_by_identifier(catalog_graph, rid)
            if resource is not None:
                display_name = get_prefLabel(resource, catalog_graph)
                if not display_name or display_name == "None":
                    display_name = get_title(resource, catalog_graph)
                if not display_name or display_name == "None":
                    display_name = rid
                display_link = create_local_link(resource, catalog_graph)

        rows.append(
            (
                str(display_name).lower(),
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


def _source_distribution_table(distributions) -> str:
    """
    Render structured distributions from source YAML.

    Expected shape:
      distributions:
        - format: csv
          access_url: https://...
          issued: 2026-06-11
    """
    if not distributions:
        return "No distributions available.\n\n"

    rows = []

    for dist in distributions:
        if not isinstance(dist, dict):
            continue

        fmt = str(dist.get("format", "")).strip() or "Not available"
        access_url = str(dist.get("access_url", "")).strip() or "Not available"
        issued = str(dist.get("issued", "")).strip() or "–"

        rows.append((fmt.lower(), fmt, access_url, issued))

    if not rows:
        return "No distributions available.\n\n"

    rows.sort(key=lambda x: x[0])

    table_str = "|===\n"
    table_str += "| Format | Access URL | Issued\n\n"

    for _, fmt, access_url, issued in rows:
        if access_url != "Not available":
            access_cell = f"link:{access_url}[{access_url}]"
        else:
            access_cell = access_url

        table_str += f"| {fmt}\n"
        table_str += f"| {access_cell}\n"
        table_str += f"| {issued}\n\n"

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

    source_distributions = source_dataset.get("distributions", [])
    if isinstance(source_distributions, dict):
        source_distributions = [source_distributions]
    if not isinstance(source_distributions, list):
        source_distributions = []

    # DEBUG MARKER
    adoc_str += "== DEBUG DATASET PAGE\n\nThis is the updated dataset page file.\n\n"

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

    if source_distributions:
        adoc_str += f"* **Distributions:** {len(source_distributions)} available (see section below)\n"
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
    adoc_str += _source_distribution_table(source_distributions)

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
