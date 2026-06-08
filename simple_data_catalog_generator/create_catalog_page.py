from pathlib import Path
import yaml

from rdflib import Graph, URIRef, RDF
from rdflib.namespace import DCAT, DCTERMS, SKOS

from simple_data_catalog_generator.create_metadata_table import create_metadata_table
from simple_data_catalog_generator.analysis_functions import create_theme_word_cloud
from simple_data_catalog_generator.page_creation_functions import (
    write_file,
    get_title,
    get_description,
    get_id,
    create_local_link,
    get_prefLabel,
    get_definition,
)


def _first_literal(graph: Graph, subject: URIRef, predicates):
    for pred in predicates:
        val = graph.value(subject, pred)
        if val is not None and str(val).strip() and str(val).strip() != "None":
            return str(val).strip()
    return ""


def _build_dataset_table(catalog_graph: Graph, catalog: URIRef) -> str:
    dataset_rows = []

    for dataset in catalog_graph.objects(catalog, DCAT.dataset):
        dataset_name = get_title(dataset, catalog_graph)
        dataset_id = get_id(dataset, catalog_graph)
        dataset_description = get_description(dataset, catalog_graph)

        dataset_use_case = _first_literal(
            catalog_graph,
            dataset,
            [
                URIRef("https://www.uuidea.eu/profiles/data-catalog/use_case"),
                URIRef("https://www.uuidea.eu/profiles/data-catalog/useCase"),
            ],
        )

        dataset_link = create_local_link(dataset, catalog_graph)
        dataset_name_display = dataset_link if dataset_link else dataset_name

        if not dataset_description or dataset_description == "None":
            dataset_description = "Not available"

        if not dataset_use_case:
            dataset_use_case = "Not available"

        dataset_rows.append(
            (
                dataset_name_display,
                dataset_id,
                dataset_use_case,
                dataset_description,
            )
        )

    if not dataset_rows:
        return "No datasets available.\n\n"

    table_str = "|===\n"
    table_str += "| Name | ID | Use Case | Description\n\n"

    for name, ds_id, use_case, description in dataset_rows:
        table_str += f"| {name}\n"
        table_str += f"| `{ds_id}`\n"
        table_str += f"| {use_case}\n"
        table_str += f"| {description}\n\n"

    table_str += "|===\n\n"
    return table_str


def _load_all_deleted_datasets():
    rows = []

    catalog_files = sorted(Path("data-catalog/user-catalogs").glob("*.yaml")) + sorted(
        Path("data-catalog/user-catalogs").glob("*.yml")
    )

    for yf in catalog_files:
        doc = yaml.safe_load(yf.read_text(encoding="utf-8")) or {}
        catalog = doc.get("catalog", {}) or {}
        catalog_id = catalog.get("id") or catalog.get("identifier") or yf.stem

        deleted_datasets = doc.get("deleted_datasets", [])
        if deleted_datasets is None:
            deleted_datasets = []

        if not isinstance(deleted_datasets, list):
            continue

        for item in deleted_datasets:
            if not isinstance(item, dict):
                continue

            rows.append(
                {
                    "catalog_id": catalog_id,
                    "id": str(item.get("id", "")).strip(),
                    "title": str(item.get("title", "")).strip(),
                    "description": str(item.get("description", "")).strip(),
                    "deleted_at": str(item.get("deleted_at", "")).strip(),
                }
            )

    return rows


def _build_deleted_dataset_table() -> str:
    deleted_rows = _load_all_deleted_datasets()

    if not deleted_rows:
        return "No deleted datasets recorded.\n\n"

    table_str = "|===\n"
    table_str += "| Name | ID | Linked Catalog ID | Deleted at | Description\n\n"

    for row in deleted_rows:
        title = row["title"] or "Not available"
        ds_id = row["id"] or "Not available"
        catalog_id = row["catalog_id"] or "Not available"
        deleted_at = row["deleted_at"] or "Not available"
        description = row["description"] or "Not available"

        table_str += f"| {title}\n"
        table_str += f"| `{ds_id}`\n"
        table_str += f"| `{catalog_id}`\n"
        table_str += f"| {deleted_at}\n"
        table_str += f"| {description}\n\n"

    table_str += "|===\n\n"
    return table_str


def _build_concept_table(catalog_graph: Graph) -> str:
    concept_rows = []

    for concept in catalog_graph.subjects(RDF.type, SKOS.Concept):
        concept_name = get_prefLabel(concept, catalog_graph)
        concept_id = get_id(concept, catalog_graph)
        concept_definition = get_definition(concept, catalog_graph)

        if not concept_definition or concept_definition == "None":
            concept_definition = "Not available"

        concept_link = create_local_link(concept, catalog_graph)
        concept_name_display = concept_link if concept_link else concept_name

        concept_rows.append((concept_name.lower(), concept_name_display, concept_id, concept_definition))

    if not concept_rows:
        return "No concepts available.\n\n"

    concept_rows.sort(key=lambda x: x[0])

    table_str = "|===\n"
    table_str += "| Name | ID | Definition\n\n"

    for _, name_display, concept_id, concept_definition in concept_rows:
        table_str += f"| {name_display}\n"
        table_str += f"| `{concept_id}`\n"
        table_str += f"| {concept_definition}\n\n"

    table_str += "|===\n\n"
    return table_str


def create_catalog_page(catalog_graph: Graph, output_dir: str = "modules/data-catalog/pages/"):
    adoc_str = str()

    catalog = None
    for datacat in catalog_graph.subjects(RDF.type, DCAT.Catalog):
        catalog = datacat

    if catalog is None:
        raise ValueError("No resource found with rdf:type dcat:Catalog")

    # Title
    adoc_str += "= " + get_title(catalog, catalog_graph) + "\n\n"

    # Description
    adoc_str += "== Description\n\n"
    desc = get_description(catalog, catalog_graph)
    if desc and desc != "None":
        adoc_str += desc + "\n\n"
    else:
        adoc_str += "No description available.\n\n"

    # Machine-readable link
    adoc_str += (
        "A machine readable version of this data catalog can be found here: "
        "xref:attachment$data-catalog.ttl[data-catalog.ttl]\n\n"
    )

    # Overview
    adoc_str += "== Overview\n\n"
    adoc_str += create_metadata_table(
        catalog_graph=catalog_graph,
        resource=catalog
    ) + "\n\n"

    # Active dataset table
    adoc_str += "== Datasets\n\n"
    adoc_str += _build_dataset_table(catalog_graph=catalog_graph, catalog=catalog)

    # Deleted dataset lineage table
    adoc_str += "== Deleted datasets\n\n"
    adoc_str += _build_deleted_dataset_table()

    # Concept table
    adoc_str += "== Concepts\n\n"
    adoc_str += _build_concept_table(catalog_graph=catalog_graph)

    # Datasets by Theme
    adoc_str += "== Datasets by Theme\n\n"
    create_theme_word_cloud(
        catalog_graph=catalog_graph,
        output_dir="modules/data-catalog/images/"
    )
    adoc_str += "image:wordcloud.svg[Theme Word Cloud]\n\n"

    write_file(
        adoc_str=adoc_str,
        resource=catalog,
        output_dir=output_dir,
        catalog_graph=catalog_graph
    )


if __name__ == "__main__":
    catalog_graph = Graph()
    catalog_graph.parse("data-catalog/data-catalog.ttl")
    create_catalog_page(catalog_graph=catalog_graph)
