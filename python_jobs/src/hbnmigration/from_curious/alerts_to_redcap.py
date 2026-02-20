"""Monitor Curious alerts and send them to REDCap."""

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
import logging
from typing import AsyncIterator, cast

import websockets

from .._config_variables import curious_variables
from ..utility_functions import ApiProtocol, get_mindlogger_token, initialize_logging

initialize_logging()
logger = logging.getLogger(__name__)


_protocols: list[ApiProtocol] = ["https", "wss"]


@dataclass
class Endpoints:
    """API Endpoints."""

    Curious: dict[ApiProtocol, curious_variables.Endpoints] = field(
        default_factory=lambda: {
            protocol: curious_variables.Endpoints(protocol=protocol)
            for protocol in _protocols
        }
    )
    """Curious API endpoints."""


_Endpoints = Endpoints()
"""Initialized Endpoints"""


@asynccontextmanager
async def connect_to_websocket(
    token: str, uri: str
) -> AsyncIterator[websockets.ClientConnection]:
    """Connect to a websocket with an auth token."""
    websocket = await websockets.connect(
        uri, subprotocols=[cast(websockets.typing.Subprotocol, f"bearer|{token}")]
    )
    try:
        yield websocket
    finally:
        await websocket.close()


async def main() -> None:
    """Send Curious alerts to REDCap."""
    tokens = get_mindlogger_token(
        _Endpoints.Curious["https"].login,
        curious_variables.Credentials().hbn_mindlogger,
        curious_variables.headers,
    )
    if not tokens:
        msg = f"Could not authenticate to {_Endpoints.Curious['https'].host}"
        raise ConnectionError(msg)
    async with connect_to_websocket(
        tokens[0], _Endpoints.Curious["wss"].alerts
    ) as websocket:
        async for message in websocket:
            logging.info(message)


if __name__ == "__main__":
    asyncio.run(main())
