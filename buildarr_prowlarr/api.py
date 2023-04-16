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
from http import HTTPStatus
from typing import TYPE_CHECKING, cast

import json5
import requests

from buildarr.state import state
from prowlarr import ApiClient, Configuration

from .exceptions import ProwlarrAPIError

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
    Create a Prowlarr API client object, and make it available within a context.

    Args:
        secrets (Optional[ProwlarrSecrets], optional): Instance secrets. Defaults to `None`.
        host_url (Optional[str], optional): Host URL, if no secrets used. Defaults to `None`.

    Yields:
        Prowlarr API client object
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
        timeout=state.request_timeout,
        allow_redirects=False,
    )

    if res.status_code != HTTPStatus.OK:
        logger.debug("GET %s -> status_code=%i res=%s", url, res.status_code, res.text)
        if res.status_code in (HTTPStatus.UNAUTHORIZED, HTTPStatus.FOUND):
            status_code: int = HTTPStatus.UNAUTHORIZED
            error_message = "Unauthorized"
        else:
            status_code = res.status_code
            error_message = f"Unexpected response with error code {res.status_code}: {res.text}"
        raise ProwlarrAPIError(
            f"Unable to retrieve 'initialize.js': {error_message}",
            status_code=status_code,
        )

    res_match = re.match(INITIALIZE_JS_RES_PATTERN, res.text)
    if not res_match:
        raise RuntimeError(f"No matches for 'initialize.js' parsing: {res.text}")
    res_json = json5.loads(res_match.group(1))

    logger.debug("GET %s -> status_code=%i res=%s", url, res.status_code, repr(res_json))

    return res_json
