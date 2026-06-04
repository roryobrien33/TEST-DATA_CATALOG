import pydantic
from rdflib import Graph, URIRef, RDF, DCAT, DCTERMS, SKOS, Namespace

from pydantic import BaseModel, Field
from typing import List, Optional

# from create_metadata_table import create_metadata_table

import os
import re
DQV = Namespace("http://www.w3.org/ns/dqv#")
ADMS= Namespace("http://www.w3.org/ns/adms#")
ODRL = Namespace("http://www.w3.org/ns/odrl/2/")



def create_local_link(resource: URIRef, catalog_graph: Graph)->str:

    id= get_id(resource=resource, catalog_graph=catalog_graph)

    rdf_type = catalog_graph.value(subject=resource, predicate=RDF.type) 

    if rdf_type== DCAT.Dataset:
        title= get_title(subject=resource, graph=catalog_graph)
        local_link = f"xref:dataset:{id}.adoc[{title}]"
    elif rdf_type== SKOS.Concept:
        pref_label=get_prefLabel(subject=resource, graph=catalog_graph)
        local_link= f"xref:concept:{id}.adoc[{pref_label}]"
    elif rdf_type== DQV.Metric:
        pref_label=get_prefLabel(subject=resource, graph=catalog_graph)        
        local_link= f"xref:metric:{id}.adoc[{pref_label}]"
    elif rdf_type== DCAT.DataService:
        title= get_title(subject=resource, graph=catalog_graph)       
        local_link= f"xref:dataservice:{id}.adoc[{title}]"  
    elif rdf_type== DCAT.DatasetSeries:
        title= get_title(subject=resource, graph=catalog_graph)       
        local_link= f"xref:dataset-series:{id}.adoc[{title}]"  
    elif rdf_type== DCAT.Catalog:
        title= get_title(subject=resource, graph=catalog_graph)       
        local_link= f"xref:data-catalog:{id}.adoc[{title}]"  
    elif rdf_type== ODRL.Policy:
        title= get_title(subject=resource, graph=catalog_graph)       
        local_link= f"xref:policy:{id}.adoc[{title}]"      
    else:
        local_link=""                
    

    return local_link


def write_file(adoc_str:str, resource: URIRef, output_dir: str, catalog_graph: Graph)->str:
    ## create filename after uri, handle most common prefix separators

    file_name= get_id(resource=resource, catalog_graph=catalog_graph)
    print(output_dir)
    output_path = os.path.join(output_dir, file_name+'.adoc')
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        f.write(adoc_str)
    add_to_nav(output_dir = output_dir, file_name=file_name, resource=resource, catalog_graph=catalog_graph)

def get_prefLabel(subject: URIRef, graph: Graph)->str:
    prefLabel= str(graph.value(subject,SKOS.prefLabel))

    return prefLabel

def get_altLabel(subject: URIRef, graph: Graph)->str:
    altLabel= str(graph.value(subject,SKOS.altLabel))
    
    return altLabel

def get_definition(subject: URIRef, graph: Graph)->str:
    definition= str(graph.value(subject,SKOS.definition))
    print(definition)
    return definition
    
def get_title(subject: URIRef, graph: Graph)->str:
    title= graph.value(subject,DCTERMS.title)

    title_str=str(title)

    if title_str == 'None':
            if '#' in str(i):
                title_str = str(i).split("#")[1]
            elif '/' in str(i):
                title_str = str(i).split("/")[-1]                
            else:
                title_str=re.sub(r'.*?\/', '/',str(i)).replace("/","")   
    return title_str

def get_status(subject: URIRef, graph: Graph)->str:
    title= graph.value(subject,ADMS.status)

    title_str=str(title)
    return title_str

def get_description(subject: URIRef, graph: Graph) ->str:
    description = graph.value(subject,DCTERMS.description)

    description_str=str(description)
    
    return description_str


def get_id(
    resource: URIRef,
    catalog_graph: Graph,
) -> str:
    """
    Extract a unique identifier for an RDF resource from its graph.

    This function attempts to retrieve a persistent identifier via the
    `DCTERMS.identifier` property. If no identifier is found, it falls back
    to generating one based on the resource's URI.

    The generation strategy depends on whether the URI contains a fragment
    identifier (`#`). If present, everything after the first '#' is used.
    Otherwise, the function normalizes the URI by:

      1. Stripping any leading path components (e.g., `http://example.org/`)
         using regex substitution to capture just the final segment
      2. Removing all slashes from that segment

    This approach aims for deterministic identifiers while providing a way
    to create them when none are explicitly stated in the graph.

    Args:
        resource: The RDF resource (URIRef) for which an identifier is required
        catalog_graph: Graph containing RDF statements about resources

    Returns:
        A string representing the unique identifier, suitable for use as part of
        a page name or link target.a
    """
    identifier = str(catalog_graph.value(URIRef(resource), DCTERMS.identifier))
    if identifier == "None":
        if "#" in str(resource):
            identifier = str(resource).split("#")[1]
        elif "/" in str(resource):
            identifier = str(resource).split("/")[-1]            
        else:
            # Normalization fallback: use final path segment without slashes
            identifier = re.sub(r".*?\/", "/", str(resource)).replace("/", "")
    return identifier


def add_to_nav(file_name: str, output_dir: str, resource: URIRef, catalog_graph: Graph):
    # print(output_dir)
    """Add a new page to the navigation file (nav.adoc)"""
    # Determine the relative path for the nav entry
    # Assuming the structure: modules/Dataset/pages/...

    name= create_local_link(resource=resource, catalog_graph=catalog_graph) + "\n\n"

    if 'modules/data-catalog/pages/' == output_dir:  
        nav_entry = f"* {name}" 

    else :
        # Extract the dataset name from the path
        nav_entry = f"*** {name}"

    nav_file_path = 'modules/data-catalog/nav.adoc'
    
    try:
        # # Read the existing content
        # with open(nav_file_path, 'r') as f:
        #     content = f.read()
        

        with open(nav_file_path, 'a') as f:
                f.write(nav_entry)
        

    except FileNotFoundError:
        ...

            

def create_nav_header(page_type: str):

    nav_file_path = 'modules/data-catalog/nav.adoc'
    nav_header= f"** {page_type} \n\n"

    with open(nav_file_path, 'a') as f:
        f.write(nav_header)

