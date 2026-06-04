# from import_catalog import parse_catalog
from rdflib import Graph, Namespace, URIRef, Literal, BNode, paths
from rdflib.namespace import FOAF, DCTERMS, DCAT, PROV, OWL, RDFS, RDF, XMLNS, SKOS, SOSA, ORG, SSN, XSD
import pandas as pd
import os
import re
# import igraph as ig
import matplotlib.pyplot as plt
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import pathlib
from simple_data_catalog_generator.page_creation_functions import get_id, get_title

def was_derived_from_graphic(catalog_graph: Graph, uri: URIRef):
    # ----------------------------------------------------------------------
    # 1️⃣  Gather the full forward‑lineage (all datasets the `uri` derives from)
    # ----------------------------------------------------------------------
    lineage_nodes: dict[str, str] = {}          # id → label
    lineage_edges: set[tuple[str, str]] = set() # (child_id, parent_id)

    def _traverse(current: URIRef):
        cur_id = get_id(resource=current, catalog_graph=catalog_graph)
        cur_label = str(catalog_graph.value(current, DCTERMS.title) or cur_id)
        lineage_nodes.setdefault(cur_id, cur_label)

        for parent in catalog_graph.objects(current, PROV.wasDerivedFrom):
            parent_id = get_id(resource=parent, catalog_graph=catalog_graph)
            parent_label = str(catalog_graph.value(parent, DCTERMS.title) or parent_id)
            lineage_nodes.setdefault(parent_id, parent_label)

            edge = (cur_id, parent_id)
            if edge not in lineage_edges:
                lineage_edges.add(edge)
                _traverse(parent)               # recurse downstream

    _traverse(URIRef(uri))

    # ----------------------------------------------------------------------
    # 2️⃣  Build the mermaid diagram – only emit each edge once
    # ----------------------------------------------------------------------
    mermaid_lines = ["graph TD"]
    for node_id, node_label in lineage_nodes.items():
        mermaid_lines.append(f"    {node_id}[{node_label}]")

    for child_id, parent_id in lineage_edges:
        mermaid_lines.append(f"    {child_id} --> {parent_id}")

    # ----------------------------------------------------------------------
    # 3️⃣  Wrap the diagram for the Markdown renderer
    # ----------------------------------------------------------------------
    diagram_str = "=== Lineage visualized\n\n"
    diagram_str += "[mermaid, lineage, svg]\n---- \n"
    diagram_str += ("\n".join(mermaid_lines) + "\n\n")
    diagram_str += "----\n\n"

    return diagram_str

# def was_derived_from_graphic(catalog_graph: Graph, uri: URIRef):
#     identifier =get_id(resource=uri, catalog_graph=catalog_graph)
#     label = str(catalog_graph.value(URIRef(uri), DCTERMS.title))
    
#     # find was derived from datasets and populate graph
#     was_derived_from = catalog_graph.objects(URIRef(uri), PROV.wasDerivedFrom)
    
#     # Build mermaid diagram as string
#     mermaid_lines = ["graph TD"]
#     mermaid_lines.append(f"    {identifier}[{label}]")
    
#     for i in was_derived_from:
#         ## TODO: make check if an edge is already in the graph
#         ## TODO: for the reverse relations: first check if the node 
#         ## is in the lineage path (wdf_indirect)
#         ## and then if the new edge is already in the graph

#         identifier2 = get_id(resource= i, catalog_graph=catalog_graph)

#         label2 = get_title(subject=i, graph= catalog_graph)

#         mermaid_lines.append(f"    {identifier2}[{label2}]")
#         mermaid_lines.append(f"    {identifier} --> {identifier2}")
        
#         # Handle indirect wasDerivedFrom relationships
#         wdf_indirect = catalog_graph.objects(i, PROV.wasDerivedFrom*'+')
#         for j in wdf_indirect:
#             label_j = get_title(subject=j, graph=catalog_graph)
#             identifier_j = get_id(resource=j, catalog_graph=catalog_graph)
            
#             mermaid_lines.append(f"    {identifier_j}[{label_j}]")
#             # mermaid_lines.append(f"    {identifier2} --> {identifier_j}")
            
#             # Handle reverse relationships
#             j_derives_from = catalog_graph.subjects(PROV.wasDerivedFrom, URIRef(j))
#             for k in j_derives_from:
#                 identifier_k = get_id(resource=k, catalog_graph=catalog_graph)
#                 label_k = get_title(subject=k, graph=catalog_graph)
#                 mermaid_lines.append(f"    {identifier_k}[{label_k}]")
#                 mermaid_lines.append(f"    {identifier_k} --> {identifier_j}")

#     diagram_str= "=== Lineage visualized\n\n"
#     diagram_str+= "[mermaid, lineage, svg]\n---- \n" 
#     diagram_str+=('\n'.join(mermaid_lines)+ "\n\n")
#     diagram_str+="----\n\n"

#     return diagram_str

def get_data_quality(catalog_graph= Graph, dataset_uri=URIRef):
    dqv_ns=Namespace("http://www.w3.org/ns/dqv#")
    quality_measurements= catalog_graph.subjects(dqv_ns.computedOn, dataset_uri)
    return quality_measurements


def supply_chain_analysis(catalog_graph=Graph, dataset_uri= URIRef): # this should be made more generic to resource as we'll also use it for dataservices
    dqv_ns = Namespace("http://www.w3.org/ns/dqv#")
    identifier = str(catalog_graph.value(URIRef(dataset_uri), DCTERMS.identifier))
    # filename = "docs/figures/" + identifier + "_supply_chain"
    path = pathlib.Path("docs/figures/")
    path.mkdir(parents=True, exist_ok=True)

    was_derived_from = catalog_graph.objects(dataset_uri, (PROV.wasDerivedFrom* '+'))
    ds_w_qm = 0 # dataset with data quality measurement
    ds_wo_qm = 0 # dataset without quality
    for wdf in was_derived_from:

        if (None, dqv_ns.computedOn, wdf) in catalog_graph:
            ds_w_qm = ds_w_qm + 1
        else:
            ds_wo_qm = ds_wo_qm + 1

    # Create mermaid pie chart
    mermaid_chart= "=== Supply Chain Analysis\n\n"
    mermaid_chart+= "[mermaid, supply-chain-analysis, svg]\n---- \n" 

    mermaid_chart += f"""pie
    title Input Datasets Quality Measurements
    "with quality measurements" : {ds_w_qm}
    "without quality measurements" : {ds_wo_qm}
"""

    mermaid_chart+="----\n\n"

    return mermaid_chart


def create_theme_word_cloud(catalog_graph: Graph, output_dir: str):
    
    themes= catalog_graph.subjects(RDF.type, SKOS.Concept)

    bag= pd.DataFrame(columns=["theme", "count"])

    
    for th in themes:
        theme_instances=catalog_graph.subjects(DCAT.theme, th)
        theme_label= catalog_graph.value(th, SKOS.prefLabel)
        themecount=0
        for ti in theme_instances:
            themecount=themecount+1

        bag.loc[len(bag)] ={"theme": theme_label, "count" : themecount}
    d = {}
    for a, x in bag.values:
        d[a] = x

    

    wordcloud = WordCloud(background_color='white')
    wordcloud.generate_from_frequencies(frequencies=d)
    plt.figure()
    plt.imshow(wordcloud, interpolation="bilinear")
    plt.axis("off")
    cloud_file_path= output_dir+ "wordcloud.svg"
    path = pathlib.Path(cloud_file_path)
    # Create directory if it doesn't exist
    path.parent.mkdir(parents=True, exist_ok=True)
    # Remove file if it already exists to ensure overwrite
    if path.exists():
        path.unlink()
    plt.savefig(cloud_file_path)

    return cloud_file_path


if __name__ == "__main__":
    catalog_graph=Graph()
    catalog_graph.parse('tests/test-data.ttl')
    print(was_derived_from_graphic(catalog_graph=catalog_graph, uri=URIRef('http://www.example.com/hdkehnf')))