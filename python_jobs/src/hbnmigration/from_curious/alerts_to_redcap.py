"""Monitor Curious alerts and send them to REDCap."""

import argparse
import asyncio
from contextlib import asynccontextmanager
import logging
from typing import Any, AsyncIterator, cast, Optional

import pandas as pd
import requests
import websockets

from .._config_variables import curious_variables
from ..utility_functions import CuriousAlert, initialize_logging

initialize_logging()
logger = logging.getLogger(__name__)


class _SynchronousArgs(argparse.Namespace):
    """Typehints for CLI args."""

    synchronous: bool
    """Run synchronous main function?"""


def _curious_authenticate() -> curious_variables.Tokens:
    """Authenticate to Curious."""
    endpoints = curious_variables.Endpoints()
    tokens = curious_variables.Tokens(
        endpoints, curious_variables.Credentials.hbn_mindlogger
    )
    if not tokens:
        msg = f"Could not authenticate to {endpoints.host}"
        raise ConnectionError(msg)
    return tokens


def parse_alert(alert: CuriousAlert) -> pd.DataFrame:
    """
    Parse an alert from Curious.

    'record' column will need to be updated from REDCap,
    'value' column will need to be updated from index from REDCap, and
    'redcap_event_name' will need to be set.
    """
    _color, message_remainder = alert["message"].split(': "', 1)
    answer, message_remainder = message_remainder.split('"', 1)
    message_remainder, item = message_remainder.rsplit(" ", 1)
    item = f"alerts_{item.lower()}"
    fields: list[tuple[str, Any]] = [("mrn", alert["secretId"]), (item, answer)]
    data: list[tuple[str, str, Any, Optional[str]]] = [
        (alert["secretId"], field_name, field_value, None)
        for field_name, field_value in fields
    ]
    return pd.DataFrame(
        data, columns=["record", "field_name", "value", "redcap_event_name"]
    )


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
    tokens = _curious_authenticate()
    endpoints = curious_variables.Endpoints(protocol="wss")
    async with connect_to_websocket(tokens.access, endpoints.alerts) as websocket:
        async for message in websocket:
            logging.info(message)


def synchronous_main() -> None:
    """Send Curious alerts to REDCap."""
    tokens = _curious_authenticate()
    response = requests.get(
        tokens.endpoints.alerts,
        headers={
            "Authorization": f"Bearer {tokens.access}",
            **curious_variables.headers,
        },
    )
    if response.status_code != requests.codes["okay"]:
        response.raise_for_status()
        return
    results: list[CuriousAlert] = response.json()["result"]
    redcap_alerts_list: list[pd.DataFrame] = []
    for alert in results:
        redcap_alerts_list.append(parse_alert(alert))
    redcap_alerts = pd.concat(redcap_alerts_list)
    print(redcap_alerts)  # noqa: T201
    # todo: get record_ids, indexes, and event
    return


def cli() -> None:
    """Run asynchronous or synchronous main function."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--asynchronous", action="store_false", dest="synchronous")
    parser.add_argument("--synchronous", action="store_true", dest="synchronous")
    parser.set_defaults(synchronous=False)
    namespace = _SynchronousArgs()
    args = parser.parse_args(namespace=namespace)
    if args.synchronous:
        synchronous_main()
    else:
        asyncio.run(main())


if __name__ == "__main__":
    cli()
