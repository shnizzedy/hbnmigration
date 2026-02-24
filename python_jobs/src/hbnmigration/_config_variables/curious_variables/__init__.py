"""Curious variables. Put secrets in `./curious_variables.py`."""

from ...utility_functions import ImportWithFallback

Credentials = ImportWithFallback.module(
    ".curious_variables", "Credentials", "...utility_functions.datatypes"
)
"""Curious credentials."""

Endpoints = ImportWithFallback.module(
    ".curious_variables", "Endpoints", "...utility_functions.datatypes"
)
"""Curious endpoints."""

headers: dict[str, str] = ImportWithFallback.literal(
    ".curious_variables", "headers", {}
)
"""Curious headers."""


__all__ = ["Credentials", "Endpoints", "headers"]
