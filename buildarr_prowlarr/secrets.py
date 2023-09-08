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
from typing import TYPE_CHECKING
from urllib.parse import urlparse

import prowlarr

from buildarr.secrets import SecretsPlugin
from buildarr.types import NonEmptyStr, Port
from prowlarr.exceptions import UnauthorizedException

from .api import get_initialize_js, prowlarr_api_client
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
    api_key: ArrApiKey

    @property
    def host_url(self) -> str:
        return f"{self.protocol}://{self.hostname}:{self.port}"

    @classmethod
    def from_url(cls, base_url: str, api_key: str) -> Self:
        url_obj = urlparse(base_url)
        hostname_port = url_obj.netloc.rsplit(":", 1)
        hostname = hostname_port[0]
        protocol = url_obj.scheme
        port = (
            int(hostname_port[1])
            if len(hostname_port) > 1
            else (443 if protocol == "https" else 80)
        )
        return cls(
            **{  # type: ignore[arg-type]
                "hostname": hostname,
                "port": port,
                "protocol": protocol,
                "api_key": api_key,
            },
        )

    @classmethod
    def get(cls, config: ProwlarrConfig) -> Self:
        if config.api_key:
            api_key = config.api_key
        else:
            try:
                api_key = get_initialize_js(host_url=config.host_url)["apiKey"]
            except ProwlarrAPIError as err:
                if err.status_code == HTTPStatus.UNAUTHORIZED:
                    raise ProwlarrSecretsUnauthorizedError(
                        "Unable to retrieve the API key for the Prowlarr instance "
                        f"at '{config.host_url}': Authentication is enabled. "
                        "Please try manually setting the "
                        "'Settings -> General -> Authentication Required' attribute "
                        "to 'Disabled for Local Addresses', or if that does not work, "
                        "explicitly define the API key in the Buildarr configuration.",
                    ) from None
                else:
                    raise
            # TODO: Switch to `prowlarr.InitializeJsApi.get_initialize_js` when fixed.
            # with prowlarr_api_client(host_url=config.host_url) as api_client:
            #     api_key = prowlarr.InitializeJsApi(api_client).get_initialize_js().api_key
        return cls(
            hostname=config.hostname,
            port=config.port,
            protocol=config.protocol,
            api_key=api_key,
        )

    def test(self) -> bool:
        with prowlarr_api_client(secrets=self) as api_client:
            try:
                prowlarr.SystemApi(api_client).get_system_status()
            except UnauthorizedException:
                return False
        return True
