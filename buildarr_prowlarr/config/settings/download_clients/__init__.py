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
Prowlarr plugin download client settings.
"""


from __future__ import annotations

import itertools

from logging import getLogger
from typing import Dict, Tuple, Type, Union

import prowlarr

from pydantic import Field
from typing_extensions import Annotated, Self

from ....api import prowlarr_api_client
from ....secrets import ProwlarrSecrets
from ...types import ProwlarrConfigBase
from .base import DownloadClient
from .torrent import (
    Aria2DownloadClient,
    DelugeDownloadClient,
    DownloadstationTorrentDownloadClient,
    FloodDownloadClient,
    HadoukenDownloadClient,
    QbittorrentDownloadClient,
    RtorrentDownloadClient,
    TorrentBlackholeDownloadClient,
    TransmissionDownloadClient,
    UtorrentDownloadClient,
    VuzeDownloadClient,
)
from .usenet import (
    DownloadstationUsenetDownloadClient,
    NzbgetDownloadClient,
    NzbvortexDownloadClient,
    PneumaticDownloadClient,
    SabnzbdDownloadClient,
    UsenetBlackholeDownloadClient,
)

logger = getLogger(__name__)

DOWNLOADCLIENT_TYPES: Tuple[Type[DownloadClient], ...] = (
    Aria2DownloadClient,
    DelugeDownloadClient,
    DownloadstationTorrentDownloadClient,
    DownloadstationUsenetDownloadClient,
    FloodDownloadClient,
    HadoukenDownloadClient,
    NzbgetDownloadClient,
    NzbvortexDownloadClient,
    PneumaticDownloadClient,
    QbittorrentDownloadClient,
    RtorrentDownloadClient,
    SabnzbdDownloadClient,
    TorrentBlackholeDownloadClient,
    TransmissionDownloadClient,
    UsenetBlackholeDownloadClient,
    UtorrentDownloadClient,
    VuzeDownloadClient,
)

DOWNLOADCLIENT_TYPE_MAP = {
    downloadclient_type._implementation.lower(): downloadclient_type
    for downloadclient_type in DOWNLOADCLIENT_TYPES
}

DownloadClientType = Union[
    DownloadstationUsenetDownloadClient,
    NzbgetDownloadClient,
    NzbvortexDownloadClient,
    PneumaticDownloadClient,
    SabnzbdDownloadClient,
    UsenetBlackholeDownloadClient,
    Aria2DownloadClient,
    DelugeDownloadClient,
    DownloadstationTorrentDownloadClient,
    FloodDownloadClient,
    HadoukenDownloadClient,
    QbittorrentDownloadClient,
    RtorrentDownloadClient,
    TorrentBlackholeDownloadClient,
    TransmissionDownloadClient,
    UtorrentDownloadClient,
    VuzeDownloadClient,
]


class ProwlarrDownloadClientsSettings(ProwlarrConfigBase):
    """
    Download clients are entirely optional in Prowlarr, but are available
    so you can manually perform grabs entirely within Prowlarr.

    In Buildarr, download clients for Prowlarr are configured in
    [much the same way](https://buildarr.github.io/plugins/sonarr/configuration/download-clients)
    as they are for Sonarr, although some attributes are different.

    The main differences are:

    * All instances of the `recent_priority` attribute are renamed to `client_priority`.
    * The `older_priority` attribute has been removed.
    * Any attribute relating to post-import management has been removed.

    Download clients that use Usenet or BitTorrent can be configured.

    ```yaml
    prowlarr:
      settings:
        download_clients:
          definitions:
            Transmission:
              type: "transmission"
              host: "transmission"
              port: 9091
              ...
    ```

    Some download clients support mapping categories within a download client
    to Prowlarr categories, to automatically classify downloads by content type.

    This can be defined in Buildarr using the `category_mappings` attribute.

    ```yaml
    prowlarr:
      settings:
        download_clients:
          definitions:
            qBittorrent:
              type: "qbittorrent"
              ...
              category_mappings:
                "movies":
                  - "Movies/HD"
                  - "Movies/SD"
                  ...
    ```
    """

    delete_unmanaged: bool = False
    """
    Automatically delete download clients not defined in Buildarr.
    """

    definitions: Dict[str, Annotated[DownloadClientType, Field(discriminator="type")]] = {}
    """
    Define download clients under this attribute.
    """

    @classmethod
    def from_remote(cls, secrets: ProwlarrSecrets) -> Self:
        with prowlarr_api_client(secrets=secrets) as api_client:
            api_downloadclients = prowlarr.DownloadClientApi(api_client).list_download_client()
            category_ids: Dict[str, int] = {
                api_category.name: api_category.id
                for api_category in itertools.chain.from_iterable(
                    api_category_group.sub_categories
                    for api_category_group in prowlarr.IndexerDefaultCategoriesApi(
                        api_client,
                    ).list_indexer_categories()
                )
            }
            tag_ids: Dict[str, int] = (
                {tag.label: tag.id for tag in prowlarr.TagApi(api_client).list_tag()}
                if any(api_downloadclient.tags for api_downloadclient in api_downloadclients)
                else {}
            )
        return cls(
            definitions={
                api_downloadclient.name: DOWNLOADCLIENT_TYPE_MAP[
                    api_downloadclient.implementation.lower()
                ]._from_remote(
                    category_ids=category_ids,
                    tag_ids=tag_ids,
                    remote_attrs=api_downloadclient.to_dict(),
                )
                for api_downloadclient in api_downloadclients
            },
        )

    def update_remote(
        self,
        tree: str,
        secrets: ProwlarrSecrets,
        remote: Self,
        check_unmanaged: bool = False,
    ) -> bool:
        # Track whether or not any changes have been made on the remote instance.
        changed = False
        # Pull API objects and metadata required during the update operation.
        with prowlarr_api_client(secrets=secrets) as api_client:
            downloadclient_api = prowlarr.DownloadClientApi(api_client)
            api_downloadclient_schemas = downloadclient_api.list_download_client_schema()
            api_downloadclients = {
                api_downloadclient.name: api_downloadclient
                for api_downloadclient in downloadclient_api.list_download_client()
            }
            category_ids: Dict[str, int] = {
                api_category.name: api_category.id
                for api_category in itertools.chain.from_iterable(
                    api_category_group.sub_categories
                    for api_category_group in prowlarr.IndexerDefaultCategoriesApi(
                        api_client,
                    ).list_indexer_categories()
                )
            }
            tag_ids: Dict[str, int] = (
                {tag.label: tag.id for tag in prowlarr.TagApi(api_client).list_tag()}
                if any(downloadclient.tags for downloadclient in self.definitions.values())
                or any(downloadclient.tags for downloadclient in remote.definitions.values())
                else {}
            )
        # Compare local definitions to their remote equivalent.
        # If a local definition does not exist on the remote, create it.
        # If it does exist on the remote, attempt an an in-place modification,
        # and set the `changed` flag if modifications were made.
        for downloadclient_name, downloadclient in self.definitions.items():
            downloadclient_tree = f"{tree}.definitions[{repr(downloadclient_name)}]"
            if downloadclient_name not in remote.definitions:
                downloadclient._create_remote(
                    tree=downloadclient_tree,
                    secrets=secrets,
                    api_downloadclient_schemas=api_downloadclient_schemas,
                    category_ids=category_ids,
                    tag_ids=tag_ids,
                    downloadclient_name=downloadclient_name,
                )
                changed = True
            elif downloadclient._update_remote(
                tree=downloadclient_tree,
                secrets=secrets,
                remote=remote.definitions[downloadclient_name],  # type: ignore[arg-type]
                api_downloadclient_schemas=api_downloadclient_schemas,
                category_ids=category_ids,
                tag_ids=tag_ids,
                api_downloadclient=api_downloadclients[downloadclient_name],
            ):
                changed = True
        # Traverse the remote definitions, and see if there are any remote definitions
        # that do not exist in the local configuration.
        # If `delete_unmanaged` is enabled, delete it from the remote.
        # If `delete_unmanaged` is disabled, just add a log entry acknowledging
        # the existence of the unmanaged definition.
        for downloadclient_name, downloadclient in remote.definitions.items():
            if downloadclient_name not in self.definitions:
                downloadclient_tree = f"{tree}.definitions[{repr(downloadclient_name)}]"
                if self.delete_unmanaged:
                    downloadclient._delete_remote(
                        tree=downloadclient_tree,
                        secrets=secrets,
                        downloadclient_id=api_downloadclients[downloadclient_name].id,
                    )
                    changed = True
                else:
                    logger.debug("%s: (...) (unmanaged)", downloadclient_tree)
        # Return whether or not the remote instance was changed.
        return changed
