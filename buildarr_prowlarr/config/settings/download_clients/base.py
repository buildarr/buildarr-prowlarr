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
Prowlarr plugin download client definition base class.
"""


from __future__ import annotations

from logging import getLogger
from typing import Any, Dict, List, Mapping, Set

import prowlarr

from buildarr.config import RemoteMapEntry
from buildarr.types import NonEmptyStr
from pydantic import PositiveInt
from typing_extensions import Self

from ....api import prowlarr_api_client
from ....secrets import ProwlarrSecrets
from ...types import ProwlarrConfigBase

logger = getLogger(__name__)


class DownloadClient(ProwlarrConfigBase):
    """
    Download clients are defined using the following format.
    Here is an example of a Transmission download client being configured.

    ```yaml
    ---

    prowlarr:
      settings:
        download_clients:
          definitions:
            Transmission: # Name of the download client
              type: "transmission" # Type of download client
              enable: true # Enable the download client in Prowlarr
              host: "transmission"
              port: 9091
              category: "prowlarr"
              # Define any other type-specific or global
              # download client attributes as needed.
    ```

    Every download client definition must have the correct `type` value defined,
    to tell Buildarr what type of download client to configure.
    The name of the download client definition is just a name, and has no meaning.

    `enable` can be set to `False` to keep the download client configured on Prowlarr,
    but disabled so that it is inactive.

    The below attributes can be defined on any type of download client.
    """

    enable: bool = True
    """
    When `True`, this download client is active and Prowlarr is able to send requests to it.
    """

    priority: PositiveInt = 1
    """
    Download client priority.

    Clients with a lower value are prioritised.
    Round-robin is used for clients with the same priority.
    """

    tags: Set[NonEmptyStr] = set()
    """
    Prowlarr tags to assign to the download clients.
    Only media under those tags will be assigned to this client.

    If no tags are assigned, all media can use the client.
    """

    _implementation: str
    _remote_map: List[RemoteMapEntry] = []

    @classmethod
    def _get_base_remote_map(
        cls,
        category_ids: Mapping[str, int],
        tag_ids: Mapping[str, int],
    ) -> List[RemoteMapEntry]:
        return [
            ("enable", "enable", {}),
            ("priority", "priority", {}),
            (
                "tags",
                "tags",
                {
                    "decoder": lambda v: set(
                        (tag for tag, tag_id in tag_ids.items() if tag_id in v),
                    ),
                    "encoder": lambda v: sorted(tag_ids[tag] for tag in v),
                },
            ),
        ]

    @classmethod
    def _category_mappings_decoder(
        cls,
        category_ids: Mapping[str, int],
        api_category_mappings: List[Dict[str, Any]],
    ) -> Dict[str, Set[str]]:
        category_mappings: Dict[str, Set[str]] = {}
        category_names = {value: key.lower() for key, value in category_ids.items()}
        for api_category_mapping in api_category_mappings:
            category_mappings[api_category_mapping["clientCategory"]] = set(
                category_names[category_id] for category_id in api_category_mapping["categories"]
            )
        return category_mappings

    @classmethod
    def _category_mappings_encoder(
        cls,
        category_ids: Mapping[str, int],
        category_mappings: Mapping[str, Set[str]],
    ) -> List[Dict[str, Any]]:
        api_category_mappings: List[Dict[str, Any]] = []
        category_ids = {key.lower(): value for key, value in category_ids.items()}
        for client_category, categories in category_mappings.items():
            api_category_mappings.append(
                {
                    "clientCategory": client_category,
                    "categories": sorted(
                        category_ids[category_name] for category_name in categories
                    ),
                },
            )
        return api_category_mappings

    @classmethod
    def _from_remote(
        cls,
        category_ids: Mapping[str, int],
        tag_ids: Mapping[str, int],
        remote_attrs: Mapping[str, Any],
    ) -> Self:
        return cls(
            **cls.get_local_attrs(
                cls._get_base_remote_map(category_ids, tag_ids) + cls._remote_map,
                remote_attrs,
            ),
        )

    def _get_api_schema(self, schemas: List[prowlarr.DownloadClientResource]) -> Dict[str, Any]:
        return {
            k: v
            for k, v in next(
                s for s in schemas if s.implementation.lower() == self._implementation.lower()
            )
            .to_dict()
            .items()
            if k not in ["id", "name"]
        }

    def _create_remote(
        self,
        tree: str,
        secrets: ProwlarrSecrets,
        api_downloadclient_schemas: List[prowlarr.DownloadClientResource],
        category_ids: Mapping[str, int],
        tag_ids: Mapping[str, int],
        downloadclient_name: str,
    ) -> None:
        api_schema = self._get_api_schema(api_downloadclient_schemas)
        set_attrs = self.get_create_remote_attrs(
            tree=tree,
            remote_map=self._get_base_remote_map(category_ids, tag_ids) + self._remote_map,
        )
        field_values: Dict[str, Any] = {
            field["name"]: field["value"] for field in set_attrs["fields"]
        }
        set_attrs["fields"] = [
            ({**f, "value": field_values[f["name"]]} if f["name"] in field_values else f)
            for f in api_schema["fields"]
        ]
        remote_attrs = {"name": downloadclient_name, **api_schema, **set_attrs}
        with prowlarr_api_client(secrets=secrets) as api_client:
            prowlarr.DownloadClientApi(api_client).create_download_client(
                download_client_resource=prowlarr.DownloadClientResource.from_dict(remote_attrs),
            )

    def _update_remote(
        self,
        tree: str,
        secrets: ProwlarrSecrets,
        remote: Self,
        api_downloadclient_schemas: List[prowlarr.DownloadClientResource],
        category_ids: Mapping[str, int],
        tag_ids: Mapping[str, int],
        api_downloadclient: prowlarr.DownloadClientResource,
    ) -> bool:
        changed, set_attrs = self.get_update_remote_attrs(
            tree=tree,
            remote=remote,
            remote_map=self._get_base_remote_map(category_ids, tag_ids) + self._remote_map,
            set_unchanged=True,
        )
        if changed:
            if "fields" in set_attrs:
                field_values: Dict[str, Any] = {
                    field["name"]: field["value"] for field in set_attrs["fields"]
                }
                set_attrs["fields"] = [
                    {**f, "value": field_values[f["name"]]}
                    for f in self._get_api_schema(api_downloadclient_schemas)["fields"]
                ]
            remote_attrs = {**api_downloadclient.to_dict(), **set_attrs}
            with prowlarr_api_client(secrets=secrets) as api_client:
                prowlarr.DownloadClientApi(api_client).update_download_client(
                    id=str(api_downloadclient.id),
                    download_client_resource=prowlarr.DownloadClientResource.from_dict(
                        remote_attrs,
                    ),
                )
            return True
        return False

    def _delete_remote(
        self,
        tree: str,
        secrets: ProwlarrSecrets,
        downloadclient_id: int,
    ) -> None:
        logger.info("%s: (...) -> (deleted)", tree)
        with prowlarr_api_client(secrets=secrets) as api_client:
            prowlarr.DownloadClientApi(api_client).delete_download_client(id=downloadclient_id)
