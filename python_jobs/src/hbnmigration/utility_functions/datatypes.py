"""Custom datatypes."""

from abc import ABC


class Endpoints(ABC):
    """Class to store Endpoints."""

    base_url: str
