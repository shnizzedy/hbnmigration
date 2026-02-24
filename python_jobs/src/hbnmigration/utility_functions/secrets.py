"""Utilities for secret management."""

import importlib
from typing import Any, Optional, TypeVar

T = TypeVar("T")


class ImportWithFallback:
    """Import with fallback."""

    @staticmethod
    def _import_any(module: str, name: str) -> Any:
        """Import `name` from `module`."""
        return getattr(
            importlib.import_module(
                module, package=__name__ if module.startswith(".") else None
            ),
            name,
        )

    @classmethod
    def module(
        cls,
        module: str,
        name: str,
        fallback_module: str,
        fallback_name: Optional[str] = None,
    ) -> Any:
        """Import with fallback module."""
        try:
            return cls._import_any(module, name)
        except (ImportError, ModuleNotFoundError, AttributeError):
            return cls._import_any(
                fallback_module, fallback_name if fallback_name else name
            )

    @classmethod
    def literal(cls, module: str, name: str, fallback: T) -> T:
        """Import with literal fallback."""
        try:
            return cls._import_any(module, name)
        except (ImportError, ModuleNotFoundError, AttributeError):
            return fallback
