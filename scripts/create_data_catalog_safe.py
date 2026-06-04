#!/usr/bin/env python3

from rdflib import Graph


def main():
    import simple_data_catalog_generator.analysis_functions as af
    import simple_data_catalog_generator.create_data_catalog as cdc

    # Load the generated TTL into an RDF graph
    catalog_graph = Graph()
    catalog_graph.parse("data-catalog/data-catalog.ttl", format="turtle")

    # Keep a reference to the original function
    original = af.create_theme_word_cloud

    # Patch the wordcloud creation so empty catalogs do not fail the build
    def safe_create_theme_word_cloud(*args, **kwargs):
        try:
            return original(*args, **kwargs)
        except ValueError as e:
            msg = str(e)
            if "We need at least 1 word to plot a word cloud" in msg and "got 0" in msg:
                return None
            raise

    af.create_theme_word_cloud = safe_create_theme_word_cloud

    # Run the vendored generator with the loaded graph
    cdc.create_data_catalog(catalog_graph=catalog_graph)


if __name__ == "__main__":
    main()
