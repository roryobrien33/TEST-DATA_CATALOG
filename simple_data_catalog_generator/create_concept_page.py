from pathlib import Path
import yaml

from rdflib import Graph, URIRef, RDF
from rdflib.namespace import SKOS, DCTERMS, DCAT

from simple_data_catalog_generator.page_creation_functions import (
    write_file,
    get_prefLabel,
    get_definition,
    get_id,
    create_local_link,
)


def _load_source_concept_yaml(concept: URIRef, catalog_graph: Graph):
    """
    Load the source concept YAML file corresponding to this concept.
    """
    concept_id = get_id(concept, catalog_graph)

    candidate_names = [concept_id]
    if ":" in concept_id:
        candidate_names.append(concept_id.split(":", 1)[1])
    if "/" in concept_id:
        candidate_names.append(concept_id.rstrip("/").split("/")[-1])
    if "#" in concept_id:
        candidate_names.append(concept_id.split("#")[-1])

    seen = set()
    candidate_names = [x for x in candidate_names if not (x in seen or seen.add(x))]

    for name in candidate_names:
        for ext in (".yaml", ".yml"):
            p = Path(f"data-catalog/concepts/{name}{ext}")
            if p.exists():
                return yaml.safe_load(p.read_text(encoding="utf-8")) or {}

    return {}


def _find_concept_resource_by_identifier(catalog_graph: Graph, concept_identifier: str):
    for concept in catalog_graph.subjects(RDF.type, SKOS.Concept):
        concept_id = str(catalog_graph.value(concept, DCTERMS.identifier) or "").strip()
        if concept_id == concept_identifier:
            return concept
    return None


def _concept_link_or_text(catalog_graph: Graph, concept_identifier: str):
    if not concept_identifier:
        return ""
    concept_resource = _find_concept_resource_by_identifier(catalog_graph, concept_identifier)
    if concept_resource is not None:
        return create_local_link(concept_resource, catalog_graph)
    return f"`{concept_identifier}`"


def create_concept_page(concept: URIRef, catalog_graph: Graph):
    adoc_str = str()

    source_doc = _load_source_concept_yaml(concept, catalog_graph)
    source_concept = source_doc.get("concept", {}) or {}

    concept_name = get_prefLabel(concept, catalog_graph)
    concept_id = get_id(concept, catalog_graph)
    concept_definition = get_definition(concept, catalog_graph)

    concept_alt_label = str(source_concept.get("altLabel", "")).strip()
    concept_example = str(source_concept.get("example", "")).strip()
    broader_id = str(source_concept.get("broader", "")).strip()
    narrower_ids = source_concept.get("narrower", [])
    if narrower_ids is None:
        narrower_ids = []
    if isinstance(narrower_ids, str):
        narrower_ids = [narrower_ids]
    if not isinstance(narrower_ids, list):
        narrower_ids = []

    # Datasets linked to this concept via dcat:theme
    themed_datasets = []
    for dataset in catalog_graph.subjects(DCAT.theme, concept):
        themed_datasets.append(create_local_link(dataset, catalog_graph))

    # Title
    adoc_str += "= " + concept_name + "\n\n"

    # Details
    adoc_str += "== Concept Details\n\n"
    adoc_str += f"* **Name:** {concept_name}\n"
    adoc_str += f"* **ID:** `{concept_id}`\n"

    if concept_definition and concept_definition != "None":
        adoc_str += f"* **Definition:** {concept_definition}\n"
    else:
        adoc_str += "* **Definition:** Not available\n"

    if concept_alt_label:
        adoc_str += f"* **Alternative label:** {concept_alt_label}\n"
    else:
        adoc_str += "* **Alternative label:** Not available\n"

    if concept_example:
        adoc_str += f"* **Example:** {concept_example}\n"
    else:
        adoc_str += "* **Example:** Not available\n"

    if broader_id:
        adoc_str += f"* **Broader concept:** {_concept_link_or_text(catalog_graph, broader_id)}\n"
    else:
        adoc_str += "* **Broader concept:** None\n"

    if narrower_ids:
        adoc_str += "* **Narrower concepts:**\n"
        for cid in narrower_ids:
            cid = str(cid).strip()
            if cid:
                adoc_str += f"** {_concept_link_or_text(catalog_graph, cid)}\n"
    else:
        adoc_str += "* **Narrower concepts:** None\n"

    adoc_str += "\n"

    # Alternative Labels section
    adoc_str += "== Alternative labels\n\n"
    if concept_alt_label:
        adoc_str += f"* {concept_alt_label}\n\n"
    else:
        adoc_str += "No alternative labels.\n\n"

    # Concept Hierarchy section
    adoc_str += "== Concept hierarchy\n\n"

    if broader_id:
        adoc_str += "* **Broader concept:**\n"
        adoc_str += f"** {_concept_link_or_text(catalog_graph, broader_id)}\n"
    else:
        adoc_str += "* **Broader concept:** None\n"

    if narrower_ids:
        adoc_str += "* **Narrower concepts:**\n"
        for cid in narrower_ids:
            cid = str(cid).strip()
            if cid:
                adoc_str += f"** {_concept_link_or_text(catalog_graph, cid)}\n"
    else:
        adoc_str += "* **Narrower concepts:** None\n"

    adoc_str += "\n"

    # Datasets with this theme
    adoc_str += "== Datasets with this theme\n\n"
    if themed_datasets:
        adoc_str += "\n".join(themed_datasets) + "\n\n"
    else:
        adoc_str += "No datasets linked to this concept.\n\n"

    write_file(
        adoc_str=adoc_str,
        resource=concept,
        output_dir='modules/concept/pages/',
        catalog_graph=catalog_graph
    )

    return 1
