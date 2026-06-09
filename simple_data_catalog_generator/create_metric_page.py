from pathlib import Path
import yaml

from rdflib import Graph, URIRef, RDF
from rdflib.namespace import DCTERMS
from rdflib import Namespace

from simple_data_catalog_generator.page_creation_functions import (
    write_file,
    get_id,
    get_title,
    get_prefLabel,
    get_definition,
)

DQV = Namespace("http://www.w3.org/ns/dqv#")


def _load_source_metric_yaml(metric: URIRef, catalog_graph: Graph):
    """
    Load the source metric YAML file corresponding to this metric.
    """
    metric_id = get_id(metric, catalog_graph)

    candidate_names = [metric_id]
    if ":" in metric_id:
        candidate_names.append(metric_id.split(":", 1)[1])
    if "/" in metric_id:
        candidate_names.append(metric_id.rstrip("/").split("/")[-1])
    if "#" in metric_id:
        candidate_names.append(metric_id.split("#")[-1])

    seen = set()
    candidate_names = [x for x in candidate_names if not (x in seen or seen.add(x))]

    for name in candidate_names:
        for ext in (".yaml", ".yml"):
            p = Path(f"data-catalog/metrics/{name}{ext}")
            if p.exists():
                return yaml.safe_load(p.read_text(encoding="utf-8")) or {}

    return {}


def create_metric_page(metric: URIRef, catalog_graph: Graph):
    adoc_str = str()

    source_doc = _load_source_metric_yaml(metric, catalog_graph)
    source_metric = source_doc.get("metric", {}) or {}

    metric_id = get_id(metric, catalog_graph)

    metric_name = get_prefLabel(metric, catalog_graph)
    if not metric_name or metric_name == "None":
        metric_name = get_title(metric, catalog_graph)
    if not metric_name or metric_name == "None":
        metric_name = metric_id

    metric_definition = get_definition(metric, catalog_graph)
    if not metric_definition or metric_definition == "None":
        metric_definition = str(source_metric.get("definition", "")).strip()

    expected_data_type = str(source_metric.get("expectedDataType", "")).strip()
    in_dimension = str(source_metric.get("inDimension", "")).strip()

    # Title
    adoc_str += "= " + metric_name + "\n\n"

    # Metric details
    adoc_str += "== Metric Details\n\n"
    adoc_str += f"* **Name:** {metric_name}\n"
    adoc_str += f"* **ID:** `{metric_id}`\n"

    if metric_definition and metric_definition != "None":
        adoc_str += f"* **Definition:** {metric_definition}\n"
    else:
        adoc_str += "* **Definition:** Not available\n"

    if expected_data_type:
        adoc_str += f"* **Expected data type:** {expected_data_type}\n"
    else:
        adoc_str += "* **Expected data type:** Not available\n"

    if in_dimension:
        adoc_str += f"* **Metric dimension:** {in_dimension}\n"
    else:
        adoc_str += "* **Metric dimension:** Not available\n"

    adoc_str += "\n"

    # Placeholder linkage section
    adoc_str += "== Linked datasets\n\n"
    adoc_str += "Metric linkage will be shown through data quality measurements.\n\n"

    write_file(
        adoc_str=adoc_str,
        resource=metric,
        output_dir="modules/metric/pages/",
        catalog_graph=catalog_graph,
    )

    return 1
