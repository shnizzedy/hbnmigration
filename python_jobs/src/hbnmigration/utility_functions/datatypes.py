"""Custom datatypes."""

from abc import ABC


class Endpoints(ABC):
    """Class to store Endpoints."""

    _base_url: str
    """Base URL."""

    @property
    def base_url(self) -> str:
        """Return base URL."""
        return self._base_url
