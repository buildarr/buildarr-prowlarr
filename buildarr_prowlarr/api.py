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
    from typing import Any, Dict, Generator, Optional, Union

    from .secrets import ProwlarrSecrets

logger = logging.getLogger(__name__)

INITIALIZE_JS_RES_PATTERN = re.compile(r"(?s)^window\.Prowlarr = ({.*});$")


@contextmanager
def prowlarr_api_client(
    *,
    secrets: Optional[ProwlarrSecrets] = None,
    host_url: Optional[str] = None,
    api_key: Optional[str] = None,
) -> Generator[ApiClient, None, None]:
    """
    Create a Prowlarr API client object, and make it available within a context.

    Args:
        secrets (Optional[ProwlarrSecrets], optional): Instance secrets. Defaults to `None`.
        host_url (Optional[str], optional): Host URL, if no secrets used. Defaults to `None`.

    Yields:
        Prowlarr API client object
    """

    configuration = Configuration(
        host=secrets.host_url if secrets else host_url,
        request_timeout=state.request_timeout,
    )

    root_logger = logging.getLogger()
    configuration.logger_format = cast(
        str,
        cast(logging.Formatter, root_logger.handlers[0].formatter)._fmt,
    )
    configuration.debug = logging.getLevelName(root_logger.level) == "DEBUG"

    if secrets:
        configuration.api_key["X-Api-Key"] = secrets.api_key.get_secret_value()
    elif api_key:
        configuration.api_key["X-Api-Key"] = api_key

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
            f"Unable to retrieve '{url}': {error_message}",
            status_code=status_code,
        )

    res_match = re.match(INITIALIZE_JS_RES_PATTERN, res.text)
    if not res_match:
        raise RuntimeError(f"No matches for 'initialize.js' parsing: {res.text}")
    res_json = json5.loads(res_match.group(1))

    logger.debug("GET %s -> status_code=%i res=%s", url, res.status_code, repr(res_json))

    return res_json


def api_get(
    secrets: Union[ProwlarrSecrets, str],
    api_url: str,
    *,
    api_key: Optional[str] = None,
    use_api_key: bool = True,
    expected_status_code: HTTPStatus = HTTPStatus.OK,
    session: Optional[requests.Session] = None,
) -> Any:
    """
    Send an API `GET` request.

    Args:
        secrets (Union[ProwlarrSecrets, str]): Secrets metadata, or host URL.
        api_url (str): API command.
        expected_status_code (HTTPStatus): Expected response status. Defaults to `200 OK`.

    Returns:
        Response object
    """

    if isinstance(secrets, str):
        host_url = secrets
        host_api_key = api_key
    else:
        host_url = secrets.host_url
        host_api_key = secrets.api_key.get_secret_value()

    if not use_api_key:
        host_api_key = None

    url = f"{host_url}/{api_url.lstrip('/')}"

    logger.debug("GET %s", url)

    if not session:
        session = requests.Session()
    res = session.get(
        url,
        headers={"X-Api-Key": host_api_key} if host_api_key else None,
        timeout=state.request_timeout,
    )
    res_json = res.json()

    logger.debug("GET %s -> status_code=%i res=%s", url, res.status_code, repr(res_json))

    if res.status_code != expected_status_code:
        api_error(method="GET", url=url, response=res)

    return res_json


def api_error(
    method: str,
    url: str,
    response: requests.Response,
    parse_response: bool = True,
) -> None:
    """
    Process an API error response.

    Args:
        method (str): HTTP method.
        url (str): API command URL.
        response (requests.Response): Response metadata.
        parse_response (bool, optional): Parse response error JSON. Defaults to True.

    Raises:
        API error
    """

    error_message = (
        f"Unexpected response with status code {response.status_code} from from '{method} {url}':"
    )
    if parse_response:
        res_json = response.json()
        try:
            error_message += f" {_api_error(res_json)}"
        except TypeError:
            for error in res_json:
                error_message += f"\n{_api_error(error)}"
        except KeyError:
            error_message += f" {res_json}"
    raise ProwlarrAPIError(error_message, status_code=response.status_code)


def _api_error(res_json: Any) -> str:
    """
    Generate an error message from a response object.

    Args:
        res_json (Any): Response object

    Returns:
        String containing one or more error messages
    """

    try:
        try:
            error_message = f"{res_json['propertyName']}: {res_json['errorMessage']}"
            try:
                error_message += f" (attempted value: {res_json['attemptedValue']})"
            except KeyError:
                pass
            return error_message
        except KeyError:
            pass
        try:
            return f"{res_json['message']}\n{res_json['description']}"
        except KeyError:
            pass
        return res_json["message"]
    except KeyError:
        return f"(Unsupported error JSON format) {res_json}"
