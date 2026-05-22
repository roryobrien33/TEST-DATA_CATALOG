#!/usr/bin/env bash
set -euo pipefail

# Always run from repo root (one level above this scripts folder)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

SCHEMA="simple_data_catalog_model/src/simple_data_catalog_model/data-catalog.yaml"
INPUT="data-catalog/data-catalog.yaml"
OUT="data-catalog/data-catalog.ttl"
PREFIX="data-catalog/prefix.yaml"

# Fail early with a clear message if paths are wrong
[[ -f "${SCHEMA}" ]] || { echo "ERROR: schema not found: ${REPO_ROOT}/${SCHEMA}" >&2; exit 1; }
[[ -f "${INPUT}"  ]] || { echo "ERROR: input YAML not found: ${REPO_ROOT}/${INPUT}"  >&2; exit 1; }
[[ -f "${PREFIX}" ]] || { echo "ERROR: prefix file not found: ${REPO_ROOT}/${PREFIX}" >&2; exit 1; }

# This MUST succeed, otherwise stop (so we don't generate misleading outputs)
uv run linkml-convert \
  -s "${SCHEMA}" \
  -t ttl \
  -o "${OUT}" \
  --prefix-file "${PREFIX}" \
  "${INPUT}"

echo "OK: wrote TTL to ${REPO_ROOT}/${OUT}"

# Optional: only run this AFTER LinkML succeeds
uv run python -m simple_data_catalog_generator.create_data_catalog
``