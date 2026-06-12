#!/usr/bin/env python3
"""
Central ID generation / normalization utilities for the data catalog.

Current conventions:

Catalog:
    <CATALOG-NAME-NORMALIZED>-<RANDOM6>
Example:
    GRID-DATA-AB12CD

Dataset:
    sdcdc:<catalog-id>-<dataset-slug>-<RANDOM6>
Example:
    sdcdc:GRID-DATA-AB12CD-voltage-timeseries-2H4KL0

Concept:
    sdcdc:concept-<slug>-<RANDOM6>
Example:
    sdcdc:concept-voltage-2H4KL0

Policy:
    sdcdc:policy-<slug>-<RANDOM6>
Example:
    sdcdc:policy-open-information-policy-7B9QX2

Metric:
    sdcdc:metric-<slug>-<RANDOM6>
Example:
    sdcdc:metric-voltage-quality-5M1ZP8
"""

from __future__ import annotations

import random
import re
from typing import Optional, Callable


# -----------------------------
# Generic helpers
# -----------------------------

def slugify(value: str) -> str:
    s = str(value or "").strip().lower()
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"[^a-z0-9-]", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s


def normalize_id_base(value: str) -> str:
    s = str(value or "").strip().upper()
    s = re.sub(r"[\s\-_]+", "-", s)
    s = re.sub(r"[^A-Z0-9-]", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s


def base36(num: int) -> str:
    if num < 0:
        raise ValueError("base36 input must be non-negative")

    chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    if num == 0:
        return "0"

    parts = []
    while num:
        num, rem = divmod(num, 36)
        parts.append(chars[rem])
    return "".join(reversed(parts))


def random_token6() -> str:
    n = random.randint(0, (36 ** 6) - 1)
    return base36(n).rjust(6, "0")


def ensure_curie(value: str, default_prefix: str = "sdcdc") -> str:
    s = str(value or "").strip()
    if not s:
        return s
    if s.startswith("http://") or s.startswith("https://"):
        return s
    if ":" in s:
        return s
    return f"{default_prefix}:{s}"


def is_iri(value: str) -> bool:
    s = str(value or "").strip()
    return s.startswith("http://") or s.startswith("https://")


def is_curie(value: str) -> bool:
    s = str(value or "").strip()
    return (":" in s) and (not is_iri(s))


def sanitize_page_id(value: str) -> str:
    s = str(value or "").strip()

    if ":" in s and not s.startswith("http://") and not s.startswith("https://"):
        s = s.split(":", 1)[1]

    if "#" in s:
        s = s.split("#")[-1]

    if "/" in s:
        s = s.rstrip("/").split("/")[-1]

    s = re.sub(r"[^A-Za-z0-9._-]", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s


def append_random_suffix(base_value: str) -> str:
    s = str(base_value or "").strip()
    if not s:
        raise ValueError("Base value for random suffix is empty")
    return f"{s}-{random_token6()}"


# -----------------------------
# Catalog IDs
# -----------------------------

def generate_catalog_id(catalog_name: str, add_random_suffix: bool = True) -> str:
    base = normalize_id_base(catalog_name)
    if not base:
        raise ValueError("Catalog name produced an empty normalized ID base")

    if add_random_suffix:
        return f"{base}-{random_token6()}"
    return base


def normalize_catalog_id(catalog_id: str) -> str:
    base = normalize_id_base(catalog_id)
    if not base:
        raise ValueError("Catalog ID produced an empty normalized value")
    return base


# -----------------------------
# Dataset IDs
# -----------------------------

def generate_dataset_id(catalog_id: str, dataset_short_id: str) -> str:
    """
    Generate a catalog-scoped dataset ID with random suffix.

    Example:
        sdcdc:GRID-DATA-AB12CD-voltage-timeseries-2H4KL0
    """
    cid = normalize_catalog_id(catalog_id)
    ds_short = slugify(dataset_short_id)
    if not ds_short:
        raise ValueError("Dataset short ID is empty after normalization")
    local = append_random_suffix(f"{cid}-{ds_short}")
    return f"sdcdc:{local}"


def normalize_dataset_id(catalog_id: str, dataset_id_value: str, add_random_suffix_for_new: bool = True) -> str:
    """
    Normalize a dataset identifier.

    Rules:
    - if already an IRI -> return as-is
    - if already a CURIE -> return as-is
    - otherwise -> generate catalog-scoped dataset ID
    """
    s = str(dataset_id_value or "").strip()
    if not s:
        return s
    if is_iri(s):
        return s
    if is_curie(s):
        return s
    if add_random_suffix_for_new:
        return generate_dataset_id(catalog_id, s)

    cid = normalize_catalog_id(catalog_id)
    ds_short = slugify(s)
    return f"sdcdc:{cid}-{ds_short}"


# -----------------------------
# Concept IDs
# -----------------------------

def generate_concept_id(concept_label: str) -> str:
    slug = slugify(concept_label)
    if not slug:
        raise ValueError("Concept label is empty after normalization")
    local = append_random_suffix(f"concept-{slug}")
    return f"sdcdc:{local}"


def normalize_concept_id(concept_id_or_label: str) -> str:
    s = str(concept_id_or_label or "").strip()
    if not s:
        return s
    if is_iri(s):
        return s
    if is_curie(s):
        return s
    if s.startswith("concept-"):
        return f"sdcdc:{s}"
    return generate_concept_id(s)


# -----------------------------
# Policy IDs
# -----------------------------

def generate_policy_id(policy_title: str) -> str:
    slug = slugify(policy_title)
    if not slug:
        raise ValueError("Policy title is empty after normalization")
    local = append_random_suffix(f"policy-{slug}")
    return f"sdcdc:{local}"


def normalize_policy_id(policy_id_or_title: str) -> str:
    s = str(policy_id_or_title or "").strip()
    if not s:
        return s
    if is_iri(s):
        return s
    if is_curie(s):
        return s
    if s.startswith("policy-"):
        return f"sdcdc:{s}"
    return generate_policy_id(s)


# -----------------------------
# Metric IDs
# -----------------------------

def generate_metric_id(metric_label: str) -> str:
    slug = slugify(metric_label)
    if not slug:
        raise ValueError("Metric label is empty after normalization")
    local = append_random_suffix(f"metric-{slug}")
    return f"sdcdc:{local}"


def normalize_metric_id(metric_id_or_label: str) -> str:
    s = str(metric_id_or_label or "").strip()
    if not s:
        return s
    if is_iri(s):
        return s
    if is_curie(s):
        return s
    if s.startswith("metric-"):
        return f"sdcdc:{s}"
    return generate_metric_id(s)


# -----------------------------
# Bulk list helpers
# -----------------------------

def parse_csv_ids(raw: Optional[str], normalizer: Callable[[str], str]) -> list[str]:
    if not raw:
        return []

    values = [x.strip() for x in str(raw).split(",") if x.strip()]
    out = []
    for v in values:
        normalized = normalizer(v)
        if normalized:
            out.append(normalized)
    return out


if __name__ == "__main__":
    print("Examples:")
    print("catalog:", generate_catalog_id("Grid Data"))
    print("dataset:", generate_dataset_id("GRID-DATA-AB12CD", "voltage-timeseries"))
    print("concept:", generate_concept_id("Voltage"))
    print("policy:", generate_policy_id("Open Information Policy"))
    print("metric:", generate_metric_id("Voltage Quality"))
    print("page id:", sanitize_page_id("sdcdc:concept-voltage-2H4KL0"))

