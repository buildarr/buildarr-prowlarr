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
Prowlarr plugin Usenet download client definitions.
"""


from __future__ import annotations

from logging import getLogger
from typing import Dict, List, Literal, Mapping, Optional, Set

from buildarr.config import RemoteMapEntry
from buildarr.types import BaseEnum, LowerCaseNonEmptyStr, NonEmptyStr, Password, Port
from pydantic import SecretStr

from .base import DownloadClient

logger = getLogger(__name__)


class NzbgetPriority(BaseEnum):
    """
    NZBGet media priority.

    Values:

    * `verylow` (Very Low)
    * `low` (Low)
    * `normal` (Normal)
    * `high` (High)
    * `veryhigh` (Very High)
    * `force` (Force)
    """

    verylow = -100
    low = -50
    normal = 0
    high = 50
    veryhigh = 100
    force = 900


class NzbvortexPriority(BaseEnum):
    """
    NZBVortex media priority.

    Values:

    * `low` (Low)
    * `normal` (Normal)
    * `high` (High)
    """

    low = -1
    normal = 0
    high = 1


class SabnzbdPriority(BaseEnum):
    """
    SABnzbd media priority.

    Values:

    * `default` (Default)
    * `paused` (Paused)
    * `low` (Low)
    * `normal` (Normal)
    * `high` (High)
    * `force` (Force)
    """

    default = -100
    paused = -2
    low = -1
    normal = 0
    high = 1
    force = 2


class UsenetDownloadClient(DownloadClient):
    """
    Usenet-based download client.
    """

    pass


class DownloadstationUsenetDownloadClient(UsenetDownloadClient):
    """
    Download client which uses Usenet via Download Station.
    """

    type: Literal["downloadstation-usenet"] = "downloadstation-usenet"
    """
    Type value associated with this kind of download client.
    """

    host: NonEmptyStr
    """
    Download Station host name.
    """

    port: Port = 5000  # type: ignore[assignment]
    """
    Download client access port.
    """

    use_ssl: bool = False
    """
    Use a secure connection when connecting to the download client.
    """

    username: NonEmptyStr
    """
    User name to use when authenticating with the download client.
    """

    password: Password
    """
    Password to use to authenticate the download client user.
    """

    category: Optional[str] = None
    """
    Associate media from Prowlarr with a category.
    Creates a `[category]` subdirectory in the output directory.

    Adding a category specific to Prowlarr avoids conflicts with unrelated non-Prowlarr downloads.
    Using a category is optional, but strongly recommended.
    """

    directory: Optional[str] = None
    """
    Optional shared folder to put downloads into.

    Leave blank, set to `null` or undefined to use the default download client location.
    """

    _implementation: str = "UsenetDownloadStation"
    _remote_map: List[RemoteMapEntry] = [
        ("host", "host", {"is_field": True}),
        ("port", "port", {"is_field": True}),
        ("use_ssl", "useSsl", {"is_field": True}),
        ("username", "username", {"is_field": True}),
        ("password", "password", {"is_field": True}),
        (
            "category",
            "category",
            {"is_field": True, "decoder": lambda v: v or None, "encoder": lambda v: v or ""},
        ),
        (
            "category",
            "tvDirectory",
            {"is_field": True, "decoder": lambda v: v or None, "encoder": lambda v: v or ""},
        ),
    ]


class NzbgetDownloadClient(UsenetDownloadClient):
    """
    NZBGet download client.
    """

    type: Literal["nzbget"] = "nzbget"
    """
    Type value associated with this kind of download client.
    """

    host: NonEmptyStr
    """
    NZBGet host name.
    """

    port: Port = 5000  # type: ignore[assignment]
    """
    Download client access port.
    """

    use_ssl: bool = False
    """
    Use a secure connection when connecting to the download client.
    """

    url_base: Optional[str] = None
    """
    Adds a prefix to the NZBGet url, e.g. `http://[host]:[port]/[url_base]/jsonrpc`.
    """

    username: NonEmptyStr
    """
    User name to use when authenticating with the download client.
    """

    password: Password
    """
    Password to use to authenticate the download client user.
    """

    category: Optional[str] = None
    """
    Associate media from Prowlarr with a category.

    Adding a category specific to Prowlarr avoids conflicts with unrelated non-Prowlarr downloads.
    Using a category is optional, but strongly recommended.
    """

    client_priority: NzbgetPriority = NzbgetPriority.normal
    """
    Priority to use when grabbing releases.

    Values:

    * `verylow`
    * `low`
    * `normal`
    * `high`
    * `veryhigh`
    * `force`
    """

    add_paused: bool = False
    """
    Add media to the download client in the paused state.

    This option requires NZBGet version 16.0 or later.
    """

    category_mappings: Dict[NonEmptyStr, Set[LowerCaseNonEmptyStr]] = {}
    """
    Category mappings for associating a category on the download client
    with the selected Prowlarr categories.
    """

    _implementation: str = "Nzbget"

    @classmethod
    def _get_base_remote_map(
        cls,
        category_ids: Mapping[str, int],
        tag_ids: Mapping[str, int],
    ) -> List[RemoteMapEntry]:
        return [
            *super()._get_base_remote_map(category_ids, tag_ids),
            ("host", "host", {"is_field": True}),
            ("port", "port", {"is_field": True}),
            ("use_ssl", "useSsl", {"is_field": True}),
            (
                "url_base",
                "urlBase",
                {"is_field": True, "decoder": lambda v: v or None, "encoder": lambda v: v or ""},
            ),
            ("username", "username", {"is_field": True}),
            ("password", "password", {"is_field": True}),
            (
                "category",
                "category",
                {"is_field": True, "decoder": lambda v: v or None, "encoder": lambda v: v or ""},
            ),
            ("client_priority", "priority", {"is_field": True}),
            ("add_paused", "addPaused", {"is_field": True}),
            (
                "category_mappings",
                "categories",
                {
                    "decoder": lambda v: cls._category_mappings_decoder(category_ids, v),
                    "encoder": lambda v: cls._category_mappings_encoder(category_ids, v),
                },
            ),
        ]


class NzbvortexDownloadClient(UsenetDownloadClient):
    """
    NZBVortex download client.
    """

    type: Literal["nzbvortex"] = "nzbvortex"
    """
    Type value associated with this kind of download client.
    """

    host: NonEmptyStr
    """
    NZBVortex host name.
    """

    port: Port = 4321  # type: ignore[assignment]
    """
    Download client access port.
    """

    url_base: Optional[str] = None
    """
    Adds a prefix to the NZBVortex url, e.g. `http://[host]:[port]/[url_base]/api`.
    """

    api_key: Password
    """
    API key to use to authenticate with the download client.
    """

    category: Optional[str] = None
    """
    Associate media from Prowlarr with a category.

    Adding a category specific to Prowlarr avoids conflicts with unrelated non-Prowlarr downloads.
    Using a category is optional, but strongly recommended.
    """

    client_priority: NzbvortexPriority = NzbvortexPriority.normal
    """
    Priority to use when grabbing releases.

    Values:

    * `low`
    * `normal`
    * `high`
    """

    category_mappings: Dict[NonEmptyStr, Set[LowerCaseNonEmptyStr]] = {}
    """
    Category mappings for associating a category on the download client
    with the selected Prowlarr categories.
    """

    _implementation: str = "NzbVortex"

    @classmethod
    def _get_base_remote_map(
        cls,
        category_ids: Mapping[str, int],
        tag_ids: Mapping[str, int],
    ) -> List[RemoteMapEntry]:
        return [
            *super()._get_base_remote_map(category_ids, tag_ids),
            ("host", "host", {"is_field": True}),
            ("port", "port", {"is_field": True}),
            (
                "url_base",
                "urlBase",
                {"is_field": True, "decoder": lambda v: v or None, "encoder": lambda v: v or ""},
            ),
            ("api_key", "apiKey", {"is_field": True}),
            (
                "category",
                "category",
                {"is_field": True, "decoder": lambda v: v or None, "encoder": lambda v: v or ""},
            ),
            ("client_priority", "priority", {"is_field": True}),
            (
                "category_mappings",
                "categories",
                {
                    "decoder": lambda v: cls._category_mappings_decoder(category_ids, v),
                    "encoder": lambda v: cls._category_mappings_encoder(category_ids, v),
                },
            ),
        ]


class PneumaticDownloadClient(UsenetDownloadClient):
    """
    Download client for the Pneumatic NZB add-on for Kodi/XMBC.
    """

    type: Literal["pneumatic"] = "pneumatic"
    """
    Type value associated with this kind of download client.
    """

    nzb_folder: NonEmptyStr
    """
    Folder in which Prowlarr will store `.nzb` files.

    This folder will need to be reachable from Kodi/XMBC.
    """

    strm_folder: NonEmptyStr
    """
    Folder from which `.strm` files will be imported by Drone.
    """

    _implementation: str = "Pneumatic"
    _remote_map: List[RemoteMapEntry] = [
        ("nzb_folder", "nzbFolder", {"is_field": True}),
        ("strm_folder", "strmFolder", {"is_field": True}),
    ]


class SabnzbdDownloadClient(UsenetDownloadClient):
    """
    SABnzbd download client.
    """

    type: Literal["sabnzbd"] = "sabnzbd"
    """
    Type value associated with this kind of download client.
    """

    host: NonEmptyStr
    """
    SABnzbd host name.
    """

    port: Port = 4321  # type: ignore[assignment]
    """
    Download client access port.
    """

    use_ssl: bool = False
    """
    Use a secure connection when connecting to the download client.
    """

    url_base: Optional[str] = None
    """
    Adds a prefix to the SABnzbd URL, e.g. `http://[host]:[port]/[url_base]/api/`.
    """

    api_key: Optional[SecretStr] = None
    """
    API key to use to authenticate with SABnzbd, if required.
    """

    username: Optional[str] = None
    """
    User name to use when authenticating with SABnzbd, if required.
    """

    password: Optional[SecretStr] = None
    """
    Password to use to authenticate with SABnzbd, if required.
    """

    category: Optional[str] = None
    """
    Associate media from Prowlarr with a category.

    Adding a category specific to Prowlarr avoids conflicts with unrelated non-Prowlarr downloads.
    Using a category is optional, but strongly recommended.
    """

    client_priority: SabnzbdPriority = SabnzbdPriority.default
    """
    Priority to use when grabbing releases.

    Values:

    * `default`
    * `paused`
    * `low`
    * `normal`
    * `high`
    * `force`
    """

    category_mappings: Dict[NonEmptyStr, Set[LowerCaseNonEmptyStr]] = {}
    """
    Category mappings for associating a category on the download client
    with the selected Prowlarr categories.
    """

    _implementation: str = "Sabnzbd"

    @classmethod
    def _get_base_remote_map(
        cls,
        category_ids: Mapping[str, int],
        tag_ids: Mapping[str, int],
    ) -> List[RemoteMapEntry]:
        return [
            *super()._get_base_remote_map(category_ids, tag_ids),
            ("host", "host", {"is_field": True}),
            ("port", "port", {"is_field": True}),
            ("use_ssl", "useSsl", {"is_field": True}),
            (
                "url_base",
                "urlBase",
                {"is_field": True, "decoder": lambda v: v or None, "encoder": lambda v: v or ""},
            ),
            (
                "api_key",
                "apiKey",
                {
                    "is_field": True,
                    "decoder": lambda v: v or None,
                    "encoder": lambda v: v.get_secret_value() if v else "",
                },
            ),
            (
                "username",
                "username",
                {"is_field": True, "decoder": lambda v: v or None, "encoder": lambda v: v or ""},
            ),
            (
                "password",
                "password",
                {
                    "is_field": True,
                    "decoder": lambda v: v or None,
                    "encoder": lambda v: v.get_secret_value() if v else "",
                },
            ),
            (
                "category",
                "category",
                {"is_field": True, "decoder": lambda v: v or None, "encoder": lambda v: v or ""},
            ),
            ("client_priority", "priority", {"is_field": True}),
            (
                "category_mappings",
                "categories",
                {
                    "decoder": lambda v: cls._category_mappings_decoder(category_ids, v),
                    "encoder": lambda v: cls._category_mappings_encoder(category_ids, v),
                },
            ),
        ]


class UsenetBlackholeDownloadClient(UsenetDownloadClient):
    """
    Usenet Blackhole download client.
    """

    type: Literal["usenet-blackhole"] = "usenet-blackhole"
    """
    Type value associated with this kind of download client.
    """

    nzb_folder: NonEmptyStr
    """
    Folder in which Prowlarr will store `.nzb` files.
    """

    _implementation: str = "UsenetBlackhole"
    _remote_map: List[RemoteMapEntry] = [("nzb_folder", "nzbFolder", {"is_field": True})]
