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
Prowlarr plugin configuration.
"""


from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional

import prowlarr

from buildarr.config import ConfigPlugin
from buildarr.types import NonEmptyStr, Port
from typing_extensions import Self

from ..api import prowlarr_api_client
from ..types import ArrApiKey, ProwlarrProtocol
from .settings import ProwlarrSettings

if TYPE_CHECKING:
    from ..secrets import ProwlarrSecrets

    class _ProwlarrInstanceConfig(ConfigPlugin[ProwlarrSecrets]):
        ...

else:

    class _ProwlarrInstanceConfig(ConfigPlugin):
        ...


class ProwlarrInstanceConfig(_ProwlarrInstanceConfig):
    """
    By default, Buildarr will look for a single instance at `http://prowlarr:9696`.
    Most configurations are different, and to accommodate those, you can configure
    how Buildarr connects to individual Prowlarr instances.

    Configuration of a single Prowlarr instance:

    ```yaml
    prowlarr:
      hostname: "prowlarr.example.com"
      port: 9696
      protocol: "http"
      settings:
        ...
    ```

    Configuration of multiple instances:

    ```yaml
    prowlarr:
      # Configuration and settings common to all instances.
      port: 9696
      settings:
        ...
      instances:
        # Prowlarr instance 1-specific configuration.
        prowlarr1:
          hostname: "prowlarr1.example.com"
          settings:
            ...
        # Prowlarr instance 2-specific configuration.
        prowlarr2:
          hostname: "prowlarr2.example.com"
          api_key: "..." # Explicitly define API key
          settings:
            ...
    ```
    """

    hostname: NonEmptyStr = "prowlarr"  # type: ignore[assignment]
    """
    Hostname of the Prowlarr instance to connect to.

    When defining a single instance using the global `prowlarr` configuration block,
    the default hostname is `prowlarr`.

    When using multiple instance-specific configurations, the default hostname
    is the name given to the instance in the `instances` attribute.

    ```yaml
    prowlarr:
      instances:
        prowlarr1: # <--- This becomes the default hostname
          ...
    ```
    """

    port: Port = 9696  # type: ignore[assignment]
    """
    Port number of the Prowlarr instance to connect to.
    """

    protocol: ProwlarrProtocol = "http"  # type: ignore[assignment]
    """
    Communication protocol to use to connect to Prowlarr.

    Values:

    * `http`
    * `https`
    """

    api_key: Optional[ArrApiKey] = None
    """
    API key to use to authenticate with the Prowlarr instance.

    If undefined or set to `None`, automatically retrieve the API key.
    This can only be done on Prowlarr instances with authentication disabled.
    """

    image: NonEmptyStr = "lscr.io/linuxserver/prowlarr"  # type: ignore[assignment]
    """
    The default Docker image URI when generating a Docker Compose file.
    """

    version: Optional[str] = None
    """
    The expected version of the Prowlarr instance.
    If undefined or set to `None`, the version is auto-detected.

    This value is also used when generating a Docker Compose file.
    When undefined or set to `None`, the version tag will be set to `latest`.
    """

    settings: ProwlarrSettings = ProwlarrSettings()
    """
    Prowlarr settings.
    Configuration options for Prowlarr itself are set within this structure.
    """

    @classmethod
    def from_remote(cls, secrets: ProwlarrSecrets) -> Self:
        with prowlarr_api_client(secrets=secrets) as api_client:
            version = prowlarr.SystemApi(api_client).get_system_status().version
        return cls(
            hostname=secrets.hostname,
            port=secrets.port,
            protocol=secrets.protocol,
            api_key=secrets.api_key,
            version=version,
            settings=ProwlarrSettings.from_remote(secrets),
        )

    def to_compose_service(self, compose_version: str, service_name: str) -> Dict[str, Any]:
        return {
            "image": f"{self.image}:{self.version or 'latest'}",
            "volumes": {service_name: "/config"},
        }


class ProwlarrConfig(ProwlarrInstanceConfig):
    """
    Prowlarr plugin global configuration class.
    """

    instances: Dict[str, ProwlarrInstanceConfig] = {}
    """
    Instance-specific Prowlarr configuration.

    Can only be defined on the global `prowlarr` configuration block.

    Globally specified configuration values apply to all instances.
    Configuration values specified on an instance-level take precedence at runtime.
    """
