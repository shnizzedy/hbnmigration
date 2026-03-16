"""Monitor Curious alerts and send them to REDCap."""

import argparse
import asyncio
from contextlib import asynccontextmanager
import logging
from typing import Any, AsyncIterator, cast, Optional

from numpy import intersect1d
import pandas as pd
import requests
import websockets

from .._config_variables import curious_variables, redcap_variables
from ..from_redcap.config import FieldList
from ..from_redcap.from_redcap import fetch_data, response_index_reverse_lookup
from ..utility_functions import (
    CuriousAlert,
    fetch_api_data,
    initialize_logging,
    redcap_api_push,
)

initialize_logging()
logger = logging.getLogger(__name__)

REDCAP_ENDPOINTS = redcap_variables.Endpoints()


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


def toggle_alerts(result: pd.DataFrame) -> pd.DataFrame:
    """Add an `{instrument}_alerts` row for each relevant respondent + instrument."""
    respondent_instruments = result["field_name"].str.extract(
        r"alerts_([^_]+(?:_[^_]+)?)_\d+", expand=False
    )
    summary = result[respondent_instruments.notna()].copy()
    summary["field_name"] = (
        respondent_instruments[respondent_instruments.notna()] + "_alerts"
    )
    summary = summary.drop_duplicates(["record", "field_name", "redcap_event_name"])
    summary["value"] = "yes"
    return pd.concat([result, summary], ignore_index=True)


async def main(partial_redcap_landing: bool = False) -> None:
    """Send Curious alerts to REDCap."""
    tokens = _curious_authenticate()
    endpoints = curious_variables.Endpoints(protocol="wss")
    async with connect_to_websocket(tokens.access, endpoints.alerts) as websocket:
        async for message in websocket:
            logging.info(message)


def synchronous_main(partial_redcap_landing: bool = False) -> None:
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
    alert_fields = redcap_alerts["field_name"].unique()
    alerts_instrument = fetch_api_data(
        REDCAP_ENDPOINTS.base_url,
        redcap_variables.headers,
        {
            "token": redcap_variables.Tokens.pid625,
            "content": "metadata",
            "forms": "ra_alerts_instrument",
            "action": "export",
            "format": "csv",
            "type": "eav",
            "csvDelimiter": "",
            "rawOrLabel": "raw",
            "rawOrLabelHeaders": "raw",
            "exportCheckboxLabel": "false",
            "exportSurveyFields": "false",
            "exportDataAccessGroups": "false",
            "returnFormat": "csv",
        },
    )
    if partial_redcap_landing:
        alert_fields = intersect1d(
            alert_fields, alerts_instrument["field_name"].unique()
        )
    redcap_fields = fetch_data(
        redcap_variables.Tokens.pid625, str(FieldList(alert_fields))
    )
    redcap_alerts["record"] = (
        redcap_alerts["record"].str.replace(r"\D", "", regex=True).astype(int)
    )
    redcap_fields["record"] = redcap_fields["record"].astype(int)
    mrn_lookup = (
        redcap_fields[redcap_fields["field_name"] == "mrn"]
        .set_index("value")["record"]
        .to_dict()
    )
    record_events = redcap_fields.groupby("record")["redcap_event_name"].first()
    result = redcap_alerts.loc[redcap_alerts["field_name"] != "mrn"].copy()
    result = result[result["field_name"].isin(redcap_fields["field_name"])]
    result["redcap_event_name"] = result["record"].map(mrn_lookup).map(record_events)
    # replace response values with REDCap option indices
    choice_lookup_tuples = [
        lookup_tuple
        for lookup_tuple in [
            response_index_reverse_lookup(row)
            for _, row in alerts_instrument.iterrows()
        ]
        if lookup_tuple
    ]
    choice_lookup: dict[tuple[str, str], int] = {
        lookup_tuple[0:2]: lookup_tuple[2] for lookup_tuple in choice_lookup_tuples
    }
    result["lookup_key"] = list(zip(result["field_name"], result["value"].str.lower()))
    result["value"] = result["lookup_key"].map(choice_lookup).fillna(result["value"])
    result = toggle_alerts(result.drop("lookup_key", axis=1))
    # set record IDs to match REDCap
    result["record"] = result["record"].map(mrn_lookup)
    # push to REDCap
    try:
        redcap_api_push(
            result,
            redcap_variables.Tokens.pid625,
            REDCAP_ENDPOINTS.base_url,
            redcap_variables.headers,
        )
        logger.info(
            "%d rows successfully updated for alerts in PID 625.", result.shape[1]
        )
    except Exception:
        logger.exception("Pushing alerts from Curious to REDCap failed.")
        raise

    return


def cli() -> None:
    """Run asynchronous or synchronous main function."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--asynchronous", action="store_false", dest="synchronous")
    parser.add_argument("--partial", action="store_true", dest="partial")
    parser.add_argument("--synchronous", action="store_true", dest="synchronous")
    parser.set_defaults(partial=False, synchronous=False)
    namespace = _SynchronousArgs()
    args = parser.parse_args(namespace=namespace)
    if args.synchronous:
        synchronous_main(args.partial)
    else:
        asyncio.run(main(args.partial))


if __name__ == "__main__":
    cli()
