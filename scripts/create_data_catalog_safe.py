#!/usr/bin/env python3
from pathlib import Path
import sys
from rdflib import Graph


def main():
    # Force Python to prefer the repo root so the vendored package is imported first
    repo_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(repo_root))

    import simple_data_catalog_generator
    import simple_data_catalog_generator.analysis_functions as af
    import simple_data_catalog_generator.create_catalog_page as ccp
    import simple_data_catalog_generator.create_data_catalog as cdc

    # Print the actual package path so it appears in the Actions log
    print("USING simple_data_catalog_generator FROM:")
    print(simple_data_catalog_generator.__file__)

    # Load the generated TTL into an RDF graph
    catalog_graph = Graph()
    catalog_graph.parse("data-catalog/data-catalog.ttl", format="turtle")

    # Keep a reference to the original function
    original = af.create_theme_word_cloud

    # Safe replacement for empty theme collections
    def safe_create_theme_word_cloud(*args, **kwargs):
        try:
            return original(*args, **kwargs)
        except ValueError as e:
            msg = str(e)
            if "We need at least 1 word to plot a word cloud" in msg and "got 0" in msg:
                return None
            raise

    # Patch both:
    # 1. the original module function
    # 2. the already-imported reference inside create_catalog_page.py
    af.create_theme_word_cloud = safe_create_theme_word_cloud
    ccp.create_theme_word_cloud = safe_create_theme_word_cloud

    # Run the vendored generator with the loaded graph
    cdc.create_data_catalog(catalog_graph=catalog_graph)


if __name__ == "__main__":
    main()
