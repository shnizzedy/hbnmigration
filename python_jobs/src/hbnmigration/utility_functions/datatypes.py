"""Custom datatypes."""

from abc import ABC
from typing import Literal


class Endpoints(ABC):
    """Class to store Endpoints."""

    _base_url: str

    @property
    def base_url(self) -> str:
        """Return base URL."""
        return self._base_url


ApiProtocol = Literal["https", "wss"]
"""API Protocol types."""
