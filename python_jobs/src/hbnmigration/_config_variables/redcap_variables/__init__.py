"""REDCap variables. Put secrets in `./redcap_variables.py`."""

from ...utility_functions import ImportWithFallback

Endpoints = ImportWithFallback.module(
    ".redcap_variables", "Endpoints", "...utility_functions"
)
"""Ripple endpoints."""

Tokens = ImportWithFallback.literal(".redcap_variables", "Tokens", NotImplemented)
"""REDCap API tokens."""

redcap_import_file = ImportWithFallback.literal(
    ".redcap_variables", "redcap_import_file", NotImplemented
)
"""Path to REDCap import data."""
