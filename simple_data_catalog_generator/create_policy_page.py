import re
from rdflib import Graph, URIRef, RDF, DCTERMS, Namespace
from simple_data_catalog_generator.page_creation_functions import write_file, get_title, get_description, create_local_link

# ODRL namespace – the test data uses the standard ODRL terms
ODRL = Namespace("http://www.w3.org/ns/odrl/2/")

# ---------------------------------------------------------------------------
# Helper – turn a list of ODRL triples (uid, description, action, assignee)
# into a simple AsciiDoc table.
def _format_odrl_section(section_name: str, items: list[tuple[str, str, str, list[str]]]) -> str:
    """
    Returns an AsciiDoc fragment:

    .Obligations
    |===
    | UID | Description | Action | Assignee(s)

    | ex:register-in-catalog | … | register | Data Provider
    |===
    """
    if not items:
        return f"*No {section_name.lower()} defined.*\n\n"

    table = f".{section_name}\n|===\n| UID | Description | Action | Assignee(s)\n\n"
    for uid, descr, action, assignees in items:
        assignee_str = ", ".join(assignees) if assignees else ""
        # escape pipe characters that would break the table
        descr = descr.replace("|", "\\|")
        table += f"| {uid} | {descr} | {action} | {assignee_str}\n"
    table += "|===\n\n"
    return table


# ---------------------------------------------------------------------------
def create_policy_page(
    policy: URIRef,
    catalog_graph: Graph
) -> None:
    """
    Generate one AsciiDoc page per ODRL policy found in *catalog_graph*.

    The page layout mimics the other ``create_*`` helpers:

    * **Title** – ``dcterms:title`` if present, otherwise the policy’s URI fragment.
    * **First paragraph** – the policy’s ``dcterms:description`` (if any).
    * **Table** – three sections (Permissions, Obligations, Prohibitions) listing the
      corresponding ODRL triples (uid, description, action, assignee).

    The file name is built from ``get_id(policy, catalog_graph)`` and the
    ``.adoc`` extension, e.g. ``open-information-policy.adoc``.
    """

    policy_uris = set()

    for s in catalog_graph.subjects(RDF.type, ODRL.Policy):
        policy_uris.add(s)

    if not policy_uris:
        # Nothing to do – silently return so the caller can continue processing
        return

    # -----------------------------------------------------------------------
    for policy in policy_uris:
        # ---- title ---------------------------------------------------------
        title = str(catalog_graph.value(policy, DCTERMS.title))
        if title is None or title == "None":
            # fall back to fragment or last path segment (same logic as get_id)
            title = str(policy)

        # ---- description (first paragraph) ---------------------------------
        description = str(catalog_graph.value(policy, DCTERMS.description))
        description = "" if description in (None, "None") else description

        # ---- collect ODRL components ----------------------------------------
        permissions = []
        obligations = []
        prohibitions = []

        # Permissions
        for perm in catalog_graph.objects(policy, ODRL.permission):
            uid = str(perm)
            descr = str(catalog_graph.value(perm, DCTERMS.description) or "")
            action = str(catalog_graph.value(perm, ODRL.action) or "")
            assignees = [
                str(a) for a in catalog_graph.objects(perm, ODRL.assignee)
            ]
            permissions.append((uid, descr, action, assignees))

        # Obligations
        for obl in catalog_graph.objects(policy, ODRL.obligation):
            uid = str(obl)
            descr = str(catalog_graph.value(obl, DCTERMS.description) or "")
            action = str(catalog_graph.value(obl, ODRL.action) or "")
            assignees = [
                str(a) for a in catalog_graph.objects(obl, ODRL.assignee)
            ]
            obligations.append((uid, descr, action, assignees))

        # Prohibitions
        for pro in catalog_graph.objects(policy, ODRL.prohibition):
            uid = str(pro)
            descr = str(catalog_graph.value(pro, DCTERMS.description) or "")
            action = str(catalog_graph.value(pro, ODRL.action) or "")
            assignees = [
                str(a) for a in catalog_graph.objects(pro, ODRL.assignee)
            ]
            prohibitions.append((uid, descr, action, assignees))

        # ---- build AsciiDoc string -----------------------------------------
        adoc = f"= {title}\n\n"

        if description:
            adoc += f"{description}\n\n"

        adoc += _format_odrl_section("Permissions", permissions)
        adoc += _format_odrl_section("Obligations", obligations)
        adoc += _format_odrl_section("Prohibitions", prohibitions)

        # ---- write file -----------------------------------------------------
        write_file(
            adoc_str=adoc,
            resource=policy,
            output_dir='modules/policy/pages/', 
            catalog_graph=catalog_graph,
        )