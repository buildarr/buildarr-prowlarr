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
Prowlarr plugin secrets file model.
"""


from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING, Optional, cast

import prowlarr

from buildarr.secrets import SecretsPlugin
from buildarr.types import NonEmptyStr, Port
from prowlarr.exceptions import UnauthorizedException
from pydantic import validator

from .api import api_get, get_initialize_js, prowlarr_api_client
from .exceptions import ProwlarrAPIError, ProwlarrSecretsUnauthorizedError
from .types import ArrApiKey, ProwlarrProtocol

if TYPE_CHECKING:
    from typing_extensions import Self

    from .config import ProwlarrConfig

    class _ProwlarrSecrets(SecretsPlugin[ProwlarrConfig]):
        ...

else:

    class _ProwlarrSecrets(SecretsPlugin):
        ...


class ProwlarrSecrets(_ProwlarrSecrets):
    """
    Prowlarr API secrets.
    """

    hostname: NonEmptyStr
    port: Port
    protocol: ProwlarrProtocol
    url_base: Optional[str]
    api_key: ArrApiKey
    version: NonEmptyStr

    @property
    def host_url(self) -> str:
        return self._get_host_url(
            protocol=self.protocol,
            hostname=self.hostname,
            port=self.port,
            url_base=self.url_base,
        )

    @validator("url_base")
    def validate_url_base(cls, value: Optional[str]) -> Optional[str]:
        return f"/{value.strip('/')}" if value and value.strip("/") else None

    @classmethod
    def _get_host_url(
        cls,
        protocol: str,
        hostname: str,
        port: int,
        url_base: Optional[str],
    ) -> str:
        return f"{protocol}://{hostname}:{port}{url_base or ''}"

    @classmethod
    def get(cls, config: ProwlarrConfig) -> Self:
        return cls.get_from_url(
            hostname=config.hostname,
            port=config.port,
            protocol=config.protocol,
            url_base=config.url_base,
            api_key=config.api_key.get_secret_value() if config.api_key else None,
        )

    @classmethod
    def get_from_url(
        cls,
        hostname: str,
        port: int,
        protocol: str,
        url_base: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> Self:
        url_base = cls.validate_url_base(url_base)
        host_url = cls._get_host_url(
            protocol=protocol,
            hostname=hostname,
            port=port,
            url_base=url_base,
        )
        if not api_key:
            unauthorized_error = (
                "Unable to retrieve the API key for the Prowlarr instance "
                f"at '{host_url}': Authentication is enabled. "
                "Please try manually setting the "
                "'Settings -> General -> Authentication Required' attribute "
                "to 'Disabled for Local Addresses', or if that does not work, "
                "explicitly define the API key in the Buildarr configuration."
            )
            # When auto-fetching the API key, try loading initialize.json first
            # (used by newer versions of Prowlarr).
            try:
                initialize_json = api_get(host_url, "/initialize.json")
            except ProwlarrAPIError as json_err:
                if json_err.status_code == HTTPStatus.NOT_FOUND:
                    # If initialize.json was not found, try initialize.js instead
                    # (used by older versions of Prowlarr).
                    try:
                        initialize_js = get_initialize_js(host_url=host_url)
                    except ProwlarrAPIError as js_err:
                        if js_err.status_code == HTTPStatus.UNAUTHORIZED:
                            raise ProwlarrSecretsUnauthorizedError(unauthorized_error) from None
                        else:
                            raise
                    else:
                        api_key = initialize_js["apiKey"]
                elif json_err.status_code == HTTPStatus.UNAUTHORIZED:
                    raise ProwlarrSecretsUnauthorizedError(unauthorized_error) from None
                else:
                    raise
            else:
                api_key = initialize_json["apiKey"]
        try:
            with prowlarr_api_client(host_url=host_url, api_key=api_key) as api_client:
                system_status = prowlarr.SystemApi(api_client).get_system_status()
        except UnauthorizedException:
            raise ProwlarrSecretsUnauthorizedError(
                (
                    f"Incorrect API key for the Prowlarr instance at '{host_url}'. "
                    "Please check that the API key is set correctly in the Buildarr "
                    "configuration, and that it is set to the value as shown in "
                    "'Settings -> General -> API Key' on the Prowlarr instance."
                ),
            ) from None
        return cls(
            hostname=cast(NonEmptyStr, hostname),
            port=cast(Port, port),
            protocol=cast(ProwlarrProtocol, protocol),
            url_base=url_base,
            api_key=cast(ArrApiKey, api_key),
            version=system_status.version,
        )

    def test(self) -> bool:
        # We already perform API requests as part of instantiating the secrets object.
        # If the object exists, then the connection test is already successful.
        return True
