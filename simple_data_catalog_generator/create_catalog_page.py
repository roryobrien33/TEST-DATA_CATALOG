from rdflib import Graph, URIRef, RDF
from rdflib.namespace import DCAT, DCTERMS 

from simple_data_catalog_generator.create_metadata_table import create_metadata_table
from simple_data_catalog_generator.analysis_functions import create_theme_word_cloud
from simple_data_catalog_generator.page_creation_functions import write_file, get_title, get_description, add_to_nav
import os
import re


def create_catalog_page(catalog_graph: Graph, output_dir: str= 'modules/data-catalog/pages/'):
    adoc_str= str()

    catalog=None
    for datacat in catalog_graph.subjects(RDF.type, DCAT.Catalog):
        catalog=datacat
    
    if catalog is None:
        raise ValueError("No resource found with rdf:type dcat:Catalog")
    
    # add title

    adoc_str += "= " + get_title(catalog, catalog_graph) + "\n\n"

    # add description
 
    adoc_str+= "== Description\n\n" + get_description(catalog, catalog_graph)+ "\n\n"

    adoc_str+= "A machine readable version of this data catalog can be found here: xref:attachment$data-catalog.ttl[data-catalog.ttl]\n\n"

    # add metadata overview


    adoc_str+= "== Overview \n\n" + create_metadata_table(catalog_graph=catalog_graph, 
                                             resource=catalog)  + "\n\n"
    # add Datasets by theme

    adoc_str= adoc_str+ "== Datasets by Theme \n\n"
    
    create_theme_word_cloud(catalog_graph=catalog_graph, 
                                             output_dir='modules/data-catalog/images/')
    adoc_str= adoc_str + "image:wordcloud.svg" + "[Theme Word Cloud]\n\n"
    # Write the adoc_str to a file
    write_file(adoc_str=adoc_str, 
               resource=catalog, 
               output_dir=output_dir, 
               catalog_graph= catalog_graph)


if __name__ == "__main__":
    catalog_graph=Graph()
    catalog_graph.parse('data-catalog/data-catalog.ttl')
    create_catalog_page(catalog_graph=catalog_graph)