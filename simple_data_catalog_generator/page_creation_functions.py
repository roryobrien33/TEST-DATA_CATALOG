import os
import re
from pathlib import Path

import yaml
from rdflib import Graph, URIRef, RDF, DCAT, DCTERMS, SKOS, Namespace

DQV = Namespace("http://www.w3.org/ns/dqv#")
ADMS = Namespace("http://www.w3.org/ns/adms#")
ODRL = Namespace("http://www.w3.org/ns/odrl/2/")


def _sanitize_page_id(value: str) -> str:
    s = (value or "").strip()

    # Prefer local part after CURIE prefix
    if ":" in s and not s.startswith("http://") and not s.startswith("https://"):
        s = s.split(":", 1)[1]

    # URI fallback
    if "#" in s:
        s = s.split("#")[-1]
    if "/" in s:
        s = s.rstrip("/").split("/")[-1]

    # Safe filename/page id
    s = re.sub(r"[^A-Za-z0-9._-]", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s


def _concept_identifier_from_source_yaml(resource: URIRef) -> str:
    resource_str = str(resource)
    candidate_names = []

    if "#" in resource_str:
        candidate_names.append(resource_str.split("#")[-1])
    if "/" in resource_str:
        candidate_names.append(resource_str.rstrip("/").split("/")[-1])

    expanded = []
    for name in candidate_names:
        expanded.append(name)

        if name.startswith("data-catalog"):
            expanded.append(name.replace("data-catalog", "", 1).lstrip("-_/"))

        if "concept-" in name:
            expanded.append(name[name.find("concept-"):])

    seen = set()
    final_candidates = []
    for c in expanded:
        c = str(c).strip()
        if c and c not in seen:
            seen.add(c)
            final_candidates.append(c)

    for name in final_candidates:
        for ext in (".yaml", ".yml"):
            path = Path(f"data-catalog/concepts/{name}{ext}")
            if path.exists():
                doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
                concept = doc.get("concept", {}) or {}
                identifier = str(concept.get("identifier", "")).strip()
                if identifier:
                    return identifier

    return ""


def get_prefLabel(subject: URIRef, graph: Graph) -> str:
    pref_label = str(graph.value(subject, SKOS.prefLabel))
    return pref_label


def get_altLabel(subject: URIRef, graph: Graph) -> str:
    alt_label = str(graph.value(subject, SKOS.altLabel))
    return alt_label


def get_definition(subject: URIRef, graph: Graph) -> str:
    definition = str(graph.value(subject, SKOS.definition))
    return definition


def get_title(subject: URIRef, graph: Graph) -> str:
    title = graph.value(subject, DCTERMS.title)
    title_str = str(title)

    if title_str == "None" or not title_str.strip():
        # fallback for concepts
        pref_label = str(graph.value(subject, SKOS.prefLabel))
        if pref_label != "None" and pref_label.strip():
            return pref_label.strip()

        subject_str = str(subject)
        if "#" in subject_str:
            title_str = subject_str.split("#")[1]
        elif "/" in subject_str:
            title_str = subject_str.rstrip("/").split("/")[-1]
        else:
            title_str = re.sub(r".*?\/", "/", subject_str).replace("/", "")

    return title_str


def get_status(subject: URIRef, graph: Graph) -> str:
    title = graph.value(subject, ADMS.status)
    title_str = str(title)
    return title_str


def get_description(subject: URIRef, graph: Graph) -> str:
    description = graph.value(subject, DCTERMS.description)
    description_str = str(description)
    return description_str


def get_id(resource: URIRef, catalog_graph: Graph) -> str:
    """
    Display identifier (full identifier if available).
    """
    identifier = str(catalog_graph.value(URIRef(resource), DCTERMS.identifier))
    if identifier != "None" and identifier.strip():
        return identifier.strip()

    rdf_type = catalog_graph.value(subject=resource, predicate=RDF.type)

    if rdf_type == SKOS.Concept:
        concept_identifier = _concept_identifier_from_source_yaml(resource)
        if concept_identifier:
            return concept_identifier

    resource_str = str(resource)

    if "#" in resource_str:
        identifier = resource_str.split("#")[1]
    elif "/" in resource_str:
        identifier = resource_str.rstrip("/").split("/")[-1]
    else:
        identifier = re.sub(r".*?\/", "/", resource_str).replace("/", "")

    return identifier


def get_page_id(resource: URIRef, catalog_graph: Graph) -> str:
    """
    Safe file/xref target id. This should be used for filenames and xrefs.
    """
    display_id = get_id(resource=resource, catalog_graph=catalog_graph)
    return _sanitize_page_id(display_id)


def create_local_link(resource: URIRef, catalog_graph: Graph) -> str:
    page_id = get_page_id(resource=resource, catalog_graph=catalog_graph)
    rdf_type = catalog_graph.value(subject=resource, predicate=RDF.type)

    if rdf_type == DCAT.Dataset:
        title = get_title(subject=resource, graph=catalog_graph)
        local_link = f"xref:dataset:{page_id}.adoc[{title}]"
    elif rdf_type == SKOS.Concept:
        pref_label = get_prefLabel(subject=resource, graph=catalog_graph)
        local_link = f"xref:concept:{page_id}.adoc[{pref_label}]"
    elif rdf_type == DQV.Metric:
        pref_label = get_prefLabel(subject=resource, graph=catalog_graph)
        local_link = f"xref:metric:{page_id}.adoc[{pref_label}]"
    elif rdf_type == DCAT.DataService:
        title = get_title(subject=resource, graph=catalog_graph)
        local_link = f"xref:dataservice:{page_id}.adoc[{title}]"
    elif rdf_type == DCAT.DatasetSeries:
        title = get_title(subject=resource, graph=catalog_graph)
        local_link = f"xref:dataset-series:{page_id}.adoc[{title}]"
    elif rdf_type == DCAT.Catalog:
        title = get_title(subject=resource, graph=catalog_graph)
        local_link = f"xref:data-catalog:{page_id}.adoc[{title}]"
    elif rdf_type == ODRL.Policy:
        title = get_title(subject=resource, graph=catalog_graph)
        local_link = f"xref:policy:{page_id}.adoc[{title}]"
    else:
        local_link = ""

    return local_link


def write_file(adoc_str: str, resource: URIRef, output_dir: str, catalog_graph: Graph) -> None:
    file_name = get_page_id(resource=resource, catalog_graph=catalog_graph)
    output_path = os.path.join(output_dir, file_name + ".adoc")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(adoc_str)

    add_to_nav(
        output_dir=output_dir,
        file_name=file_name,
        resource=resource,
        catalog_graph=catalog_graph,
    )


def add_to_nav(file_name: str, output_dir: str, resource: URIRef, catalog_graph: Graph):
    name = create_local_link(resource=resource, catalog_graph=catalog_graph) + "\n\n"

    if output_dir == "modules/data-catalog/pages/":
        nav_entry = f"* {name}"
    else:
        nav_entry = f"*** {name}"

    nav_file_path = "modules/data-catalog/nav.adoc"

    try:
        with open(nav_file_path, "a", encoding="utf-8") as f:
            f.write(nav_entry)
    except FileNotFoundError:
        pass


def create_nav_header(page_type: str):
    nav_file_path = "modules/data-catalog/nav.adoc"
    nav_header = f"** {page_type} \n\n"

    with open(nav_file_path, "a", encoding="utf-8") as f:
        f.write(nav_header)
