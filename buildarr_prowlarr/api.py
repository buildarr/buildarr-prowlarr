# Copyright (C) 2023 Callum Dickinson
#
# Buildarr is free software: you can redistribute it and/or modify it under the terms of the
# GNU General Public License as published by the Free Software Foundation,
# either version 3 of the License, or (at your option) any later version.
#
# Buildarr is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with Buildarr.
# If not, see <https://www.gnu.org/licenses/>.


"""
Prowlarr plugin API functions.
"""


from __future__ import annotations

import logging
import re

from contextlib import contextmanager
from typing import TYPE_CHECKING, cast

import json5
import requests

from buildarr.state import state
from prowlarr import ApiClient, Configuration

if TYPE_CHECKING:
    from typing import Any, Dict, Generator, Optional

    from .secrets import ProwlarrSecrets

logger = logging.getLogger(__name__)

INITIALIZE_JS_RES_PATTERN = re.compile(r"(?s)^window\.Prowlarr = ({.*});$")


@contextmanager
def prowlarr_api_client(
    *,
    secrets: Optional[ProwlarrSecrets] = None,
    host_url: Optional[str] = None,
) -> Generator[ApiClient, None, None]:
    """
    _summary_

    _extended_summary_

    Args:
        secrets (Optional[ProwlarrSecrets], optional): _description_. Defaults to None.
        host_url (Optional[str], optional): _description_. Defaults to None.

    Returns:
        _type_: _description_

    Yields:
        Generator[ApiCient, None, None]: _description_
    """

    configuration = Configuration(host=secrets.host_url if secrets else host_url)

    root_logger = logging.getLogger()
    configuration.logger_format = cast(
        str,
        cast(logging.Formatter, root_logger.handlers[0].formatter)._fmt,
    )
    configuration.debug = logging.getLevelName(root_logger.level) == "DEBUG"

    if secrets:
        configuration.api_key["X-Api-Key"] = secrets.api_key.get_secret_value()

    with ApiClient(configuration) as api_client:
        yield api_client


def get_initialize_js(host_url: str, api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Get the Prowlarr session initialisation metadata, including the API key.

    Args:
        host_url (str): Prowlarr instance URL.
        api_key (str): Prowlarr instance API key, if required. Defaults to `None`.

    Returns:
        Session initialisation metadata
    """

    url = f"{host_url}/initialize.js"
    logger.debug("GET %s", url)
    res = requests.get(
        url,
        headers={"X-Api-Key": api_key} if api_key else None,
        timeout=state.config.buildarr.request_timeout,
    )
    res_match = re.match(INITIALIZE_JS_RES_PATTERN, res.text)
    if not res_match:
        raise RuntimeError(f"No matches for initialize.js parsing: {res.text}")
    res_json = json5.loads(res_match.group(1))
    logger.debug("GET %s -> status_code=%i res=%s", url, res.status_code, repr(res_json))
    return res_json
