"""Typestubs for secret REDCap variables."""

from dataclasses import dataclass
from pathlib import Path

from ...utility_functions import Endpoints as EndpointsABC

class Endpoints(EndpointsABC):
    def __init__(self) -> None: ...
    @property
    def base_url(self) -> str: ...

headers: dict[str, str]

@dataclass
class Tokens:
    pid247: str
    pid757: str

redcap_import_file: Path
redcap_update_file: Path
