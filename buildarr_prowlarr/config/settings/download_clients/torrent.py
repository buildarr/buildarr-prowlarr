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
Prowlarr plugin torrent download client definitions.
"""


from __future__ import annotations

from logging import getLogger
from typing import Any, Dict, List, Literal, Mapping, Optional, Set

from buildarr.config import RemoteMapEntry
from buildarr.types import BaseEnum, NonEmptyStr, Password, Port
from pydantic import validator

from ....types import LowerCaseNonEmptyStr
from .base import DownloadClient

logger = getLogger(__name__)


class DelugePriority(BaseEnum):
    """
    Deluge queue priority.

    Values:

    * `last` (Last)
    * `first` (First)
    """

    last = 0
    first = 1


class FloodMediaTag(BaseEnum):
    """
    Type of tag to set on media within Flood.

    Multiple can be specified at a time.

    Values:

    * `title-slug` (Title Slug)
    * `quality` (Quality)
    * `language` (Language)
    * `release-group` (Release Group)
    * `year` (Year)
    * `indexer` (Indexer)
    * `network` (Network)
    """

    title_slug = 0
    quality = 1
    language = 2
    release_group = 3
    year = 4
    indexer = 5
    network = 6


class FreeboxPriority(BaseEnum):
    last = 0
    first = 1


class QbittorrentPriority(BaseEnum):
    """
    qBittorrent queue priority.

    Values:

    * `last` (Last)
    * `first` (First)
    """

    last = 0
    first = 1


class QbittorrentState(BaseEnum):
    """
    qBittorrent initial state.

    Values:

    * `start` (Start)
    * `force-start` (Force Start)
    * `pause` (Pause)
    """

    start = 0
    force_start = 1
    pause = 2


class RtorrentPriority(BaseEnum):
    """
    RTorrent media priority.

    Values:

    * `verylow` (Very Low)
    * `low` (Low)
    * `normal` (Normal)
    * `high` (High)
    """

    verylow = 0
    low = 1
    normal = 2
    high = 3


class TransmissionPriority(BaseEnum):
    """
    Transmission queue priority.

    Values:

    * `last` (Last)
    * `first` (First)
    """

    last = 0
    first = 1


class UtorrentPriority(BaseEnum):
    """
    uTorrent queue priority.

    Values:

    * `last` (Last)
    * `first` (First)
    """

    last = 0
    first = 1


class UtorrentState(BaseEnum):
    """
    uTorrent initial state.

    Values:

    * `start` (Start)
    * `force-start` (Force Start)
    * `pause` (Pause)
    * `stop` (Stop)
    """

    start = 0
    force_start = 1
    pause = 2
    stop = 3


class TorrentDownloadClient(DownloadClient):
    """
    Torrent-based download client.
    """

    pass


class Aria2DownloadClient(TorrentDownloadClient):
    """
    Aria2 download client.
    """

    type: Literal["aria2"] = "aria2"
    """
    Type value associated with this kind of download client.
    """

    host: NonEmptyStr
    """
    Aria2 host name.
    """

    port: Port = 6800  # type: ignore[assignment]
    """
    Download client access port.
    """

    use_ssl: bool = False
    """
    Use a secure connection when connecting to the download client.
    """

    rpc_path: NonEmptyStr = "/rpc"  # type: ignore[assignment]
    """
    XML RPC path in the Aria2 client URL.
    """

    secret_token: Password
    """
    Secret token to use to authenticate with the download client.
    """

    _implementation: str = "Aria2"
    _remote_map: List[RemoteMapEntry] = [
        ("host", "host", {"is_field": True}),
        ("port", "port", {"is_field": True}),
        ("use_ssl", "useSsl", {"is_field": True}),
        ("rpc_path", "rpcPath", {"is_field": True}),
        ("secret_token", "secretToken", {"is_field": True}),
    ]


class DelugeDownloadClient(TorrentDownloadClient):
    """
    Deluge download client.
    """

    type: Literal["deluge"] = "deluge"
    """
    Type value associated with this kind of download client.
    """

    host: NonEmptyStr
    """
    Deluge host name.
    """

    port: Port = 8112  # type: ignore[assignment]
    """
    Download client access port.
    """

    use_ssl: bool = False
    """
    Use a secure connection when connecting to the download client.
    """

    url_base: Optional[str] = None
    """
    Adds a prefix to the Deluge JSON URL, e.g. `http://[host]:[port]/[url_base]/json`.
    """

    password: Password
    """
    Password to use to authenticate the download client user.
    """

    category: Optional[str] = "prowlarr"
    """
    Associate media from Prowlarr with a category.

    Adding a category specific to Prowlarr avoids conflicts with unrelated non-Prowlarr downloads.
    Using a category is optional, but strongly recommended.
    """

    client_priority: DelugePriority = DelugePriority.last
    """
    Priority to use when grabbing releases.

    Values:

    * `last`
    * `first`
    """

    category_mappings: Dict[NonEmptyStr, Set[LowerCaseNonEmptyStr]] = {}
    """
    Category mappings for associating a category on the download client
    with the selected Prowlarr categories.
    """

    _implementation: str = "Deluge"

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
            ("password", "password", {"is_field": True}),
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


class DownloadstationTorrentDownloadClient(TorrentDownloadClient):
    """
    Download client which uses torrents via Download Station.
    """

    type: Literal["downloadstation-torrent"] = "downloadstation-torrent"
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

    _implementation: str = "TorrentDownloadStation"
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


class FloodDownloadClient(TorrentDownloadClient):
    """
    Flood download client.
    """

    type: Literal["flood"] = "flood"
    """
    Type value associated with this kind of download client.
    """

    host: NonEmptyStr
    """
    Flood host name.
    """

    port: Port = 3000  # type: ignore[assignment]
    """
    Download client access port.
    """

    use_ssl: bool = False
    """
    Use a secure connection when connecting to the download client.
    """

    url_base: Optional[str] = None
    """
    Optionally adds a prefix to Flood API, such as `[protocol]://[host]:[port]/[url_base]api`.
    """

    username: NonEmptyStr
    """
    User name to use when authenticating with the download client.
    """

    password: Password
    """
    Password to use to authenticate the download client user.
    """

    destination: Optional[str] = None
    """
    Manually specified download destination.
    """

    flood_tags: Set[NonEmptyStr] = {"prowlarr"}  # type: ignore[arg-type]
    """
    Initial tags of a download within Flood.

    To be recognized, a download must have all initial tags.
    This avoids conflicts with unrelated downloads.
    """

    additional_tags: Set[FloodMediaTag] = set()
    """
    Adds properties of media as tags within Flood.
    """

    add_paused: bool = False
    """
    Add media to the download client in the Paused state.
    """

    category_mappings: Dict[NonEmptyStr, Set[LowerCaseNonEmptyStr]] = {}
    """
    Category mappings for associating a category on the download client
    with the selected Prowlarr categories.
    """

    _implementation: str = "Flood"

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
                "destination",
                "destination",
                {"is_field": True, "decoder": lambda v: v or None, "encoder": lambda v: v or ""},
            ),
            ("flood_tags", "tags", {"is_field": True, "encoder": sorted}),
            (
                "additional_tags",
                "additionalTags",
                {
                    "is_field": True,
                    "decoder": lambda v: set(FloodMediaTag(t) for t in v),
                    "encoder": lambda v: sorted(t.value for t in v),
                },
            ),
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


class FreeboxDownloadClient(TorrentDownloadClient):
    """
    Download client for connecting to a Freebox instance.
    """

    type: Literal["freebox"] = "freebox"
    """
    Type value associated with this kind of download client.
    """

    host: NonEmptyStr = "mafreebox.freebox.fr"  # type: ignore[assignment]
    """
    Hostname or host IP address of the Freebox.

    The default of `mafreebox.freebox.fr` will only work if on the same network.
    """

    port: Port = 443  # type: ignore[assignment]
    """
    Freebox access port.

    Set to the HTTPS default port as Freebox uses HTTPS by default.
    """

    use_ssl: bool = True
    """
    Use a secure connection when connecting to the Freebox API.
    """

    api_url: NonEmptyStr = "/api/v1"  # type: ignore[assignment]
    """
    Define Freebox API base URL with API version, e.g. `http[s]://<host>:<port>/<api_url>/`.
    """

    app_id: NonEmptyStr
    """
    App ID used to authenticate with the Freebox.
    """

    app_token: Password
    """
    Unique token used to authenticate with the Freebox.
    """

    destination_directory: Optional[str] = None
    """
    Optional location to put downloads in, on the Freebox node.

    Leave blank, undefined or set to `null` to use the default Freebox download location.
    """

    category: Optional[str] = None
    """
    Default category to classify downloads under if no category mappings apply to it.

    This will create a `[category]` subdirectory in the output directory.
    Adding a category specific to Prowlarr avoids conflicts with unrelated non-Prowlarr downloads.
    """

    client_priority: FreeboxPriority = FreeboxPriority.last
    """
    Priority to use when adding a download to the client.
    """

    add_paused: bool = False
    """
    Add media to the download client in the Paused state.
    """

    category_mappings: Dict[NonEmptyStr, Set[LowerCaseNonEmptyStr]] = {}
    """
    Category mappings for associating a category on the download client
    with the selected Prowlarr categories.
    """

    _implementation: str = "TorrentFreeboxDownload"

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
            ("api_url", "apiUrl", {"is_field": True}),
            ("app_id", "appId", {"is_field": True}),
            ("app_token", "appToken", {"is_field": True}),
            (
                "destination_directory",
                "destinationDirectory",
                {"is_field": True, "decoder": lambda v: v or None, "encoder": lambda v: v or ""},
            ),
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


class HadoukenDownloadClient(TorrentDownloadClient):
    """
    Hadouken download client.
    """

    type: Literal["hadouken"] = "hadouken"
    """
    Type value associated with this kind of download client.
    """

    host: NonEmptyStr
    """
    Hadouken host name.
    """

    port: Port = 7070  # type: ignore[assignment]
    """
    Download client access port.
    """

    use_ssl: bool = False
    """
    Use a secure connection when connecting to the download client.
    """

    url_base: Optional[str] = None
    """
    Adds a prefix to the Hadouken url, e.g. `http://[host]:[port]/[url_base]/api`.
    """

    username: NonEmptyStr
    """
    User name to use when authenticating with the download client.
    """

    password: Password
    """
    Password to use to authenticate the download client user.
    """

    category: NonEmptyStr = "prowlarr"  # type: ignore[assignment]
    """
    Associate media from Prowlarr with a category.

    Adding a category specific to Prowlarr avoids conflicts with unrelated non-Prowlarr downloads.
    Using a category is optional, but strongly recommended.
    """

    category_mappings: Dict[NonEmptyStr, Set[LowerCaseNonEmptyStr]] = {}
    """
    Category mappings for associating a category on the download client
    with the selected Prowlarr categories.
    """

    _implementation: str = "Hadouken"

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
            ("category", "category", {"is_field": True}),
            (
                "category_mappings",
                "categories",
                {
                    "decoder": lambda v: cls._category_mappings_decoder(category_ids, v),
                    "encoder": lambda v: cls._category_mappings_encoder(category_ids, v),
                },
            ),
        ]


class QbittorrentDownloadClient(TorrentDownloadClient):
    """
    qBittorrent download client.
    """

    type: Literal["qbittorrent"] = "qbittorrent"
    """
    Type value associated with this kind of download client.
    """

    host: NonEmptyStr
    """
    qBittorrent host name.
    """

    port: Port = 8080  # type: ignore[assignment]
    """
    Download client access port.
    """

    use_ssl: bool = False
    """
    Use a secure connection when connecting to the download client.
    """

    url_base: Optional[str] = None
    """
    Adds a prefix to the qBittorrent URL, e.g. `http://[host]:[port]/[url_base]/api`.
    """

    username: NonEmptyStr
    """
    User name to use when authenticating with the download client.
    """

    password: Password
    """
    Password to use to authenticate the download client user.
    """

    category: Optional[str] = "prowlarr"
    """
    Associate media from Prowlarr with a category.

    Adding a category specific to Prowlarr avoids conflicts with unrelated non-Prowlarr downloads.
    Using a category is optional, but strongly recommended.
    """

    client_priority: QbittorrentPriority = QbittorrentPriority.last
    """
    Priority to use when grabbing releases.

    Values:

    * `last`
    * `first`
    """

    initial_state: QbittorrentState = QbittorrentState.start
    """
    Initial state for torrents added to qBittorrent.

    Note that forced torrents do not abide by seed restrictions.
    """

    category_mappings: Dict[NonEmptyStr, Set[LowerCaseNonEmptyStr]] = {}
    """
    Category mappings for associating a category on the download client
    with the selected Prowlarr categories.
    """

    _implementation: str = "QBittorrent"

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
            ("initial_state", "initialState", {"is_field": True}),
            (
                "category_mappings",
                "categories",
                {
                    "decoder": lambda v: cls._category_mappings_decoder(category_ids, v),
                    "encoder": lambda v: cls._category_mappings_encoder(category_ids, v),
                },
            ),
        ]


class RtorrentDownloadClient(TorrentDownloadClient):
    """
    RTorrent (ruTorrent) download client.
    """

    type: Literal["rtorrent", "rutorrent"] = "rtorrent"
    """
    Type value associated with this kind of download client.
    """

    host: NonEmptyStr
    """
    RTorrent host name.
    """

    port: Port = 8080  # type: ignore[assignment]
    """
    Download client access port.
    """

    use_ssl: bool = False
    """
    Use a secure connection when connecting to the download client.
    """

    url_base: NonEmptyStr = "RPC2"  # type: ignore[assignment]
    """
    Path to the XMLRPC endpoint, e.g. `http(s)://[host]:[port]/[url_base]`.

    When using RTorrent this usually is `RPC2` or `plugins/rpc/rpc.php`.
    """

    username: NonEmptyStr
    """
    User name to use when authenticating with the download client.
    """

    password: Password
    """
    Password to use to authenticate the download client user.
    """

    category: Optional[str] = "prowlarr"
    """
    Associate media from Prowlarr with a category.

    Adding a category specific to Prowlarr avoids conflicts with unrelated non-Prowlarr downloads.
    Using a category is optional, but strongly recommended.
    """

    directory: Optional[str] = None
    """
    Optional shared folder to put downloads into.

    Leave blank, set to `null` or undefined to use the default download client location.
    """

    client_priority: RtorrentPriority = RtorrentPriority.normal
    """
    Priority to use when grabbing releases.

    Values:

    * `verylow`
    * `low`
    * `normal`
    * `high`
    """

    add_stopped: bool = False
    """
    Enabling will add torrents and magnets to RTorrent in a stopped state.

    This may break magnet files.
    """

    category_mappings: Dict[NonEmptyStr, Set[LowerCaseNonEmptyStr]] = {}
    """
    Category mappings for associating a category on the download client
    with the selected Prowlarr categories.
    """

    _implementation: str = "RTorrent"

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
            ("url_base", "urlBase", {"is_field": True}),
            ("username", "username", {"is_field": True}),
            ("password", "password", {"is_field": True}),
            (
                "category",
                "category",
                {"is_field": True, "decoder": lambda v: v or None, "encoder": lambda v: v or ""},
            ),
            (
                "directory",
                "directory",
                {"is_field": True, "decoder": lambda v: v or None, "encoder": lambda v: v or ""},
            ),
            ("client_priority", "recentTvPriority", {"is_field": True}),
            ("add_stopped", "addStopped", {"is_field": True}),
            (
                "category_mappings",
                "categories",
                {
                    "decoder": lambda v: cls._category_mappings_decoder(category_ids, v),
                    "encoder": lambda v: cls._category_mappings_encoder(category_ids, v),
                },
            ),
        ]


class TorrentBlackholeDownloadClient(TorrentDownloadClient):
    """
    Torrent Blackhole download client.
    """

    type: Literal["torrent-blackhole"] = "torrent-blackhole"
    """
    Type value associated with this kind of download client.
    """

    torrent_folder: NonEmptyStr
    """
    Folder in which Prowlarr will store `.torrent` files.
    """

    save_magnet_files: bool = False
    """
    Save the magnet link if no `.torrent` file is available.

    Only useful if the download client supports magnets saved to a file.
    """

    magnet_file_extension: NonEmptyStr = ".magnet"  # type: ignore[assignment]
    """
    Extension to use for magnet links.
    """

    _implementation: str = "TorrentBlackhole"
    _remote_map: List[RemoteMapEntry] = [
        ("torrent_folder", "torrentFolder", {"is_field": True}),
        ("save_magnet_files", "saveMagnetFiles", {"is_field": True}),
        ("magnet_file_extension", "magnetFileExtension", {"is_field": True}),
    ]


class TransmissionDownloadClientBase(TorrentDownloadClient):
    """
    Configuration options common to both Transmission and Vuze download clients:
    """

    host: NonEmptyStr
    """
    Transmission/Vuze host name.
    """

    port: Port = 9091  # type: ignore[assignment]
    """
    Download client access port.
    """

    use_ssl: bool = False
    """
    Use a secure connection when connecting to the download client.
    """

    url_base: NonEmptyStr = "/transmission/"  # type: ignore[assignment]
    """
    Adds a prefix to the Transmission/Vuze RPC url, e.g.`http://[host]:[port][url_base]rpc`.

    This is set by default in most clients to `/transmission/`.
    """

    username: Optional[str] = None
    """
    User name to use when authenticating with the download client, if required.
    """

    password: Optional[Password] = None
    """
    Password to use to authenticate the download client user, if required.
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

    client_priority: TransmissionPriority = TransmissionPriority.last
    """
    Priority to use when grabbing releases.

    Values:

    * `last`
    * `first`
    """

    add_paused: bool = False
    """
    Add media to the download client in the Paused state.
    """

    _remote_map: List[RemoteMapEntry] = [
        ("host", "host", {"is_field": True}),
        ("port", "port", {"is_field": True}),
        ("use_ssl", "useSsl", {"is_field": True}),
        ("url_base", "urlBase", {"is_field": True}),
        (
            "username",
            "username",
            {"is_field": True, "decoder": lambda v: v or None, "encoder": lambda v: v or ""},
        ),
        ("password", "password", {"is_field": True, "field_default": None}),
        (
            "category",
            "category",
            {"is_field": True, "decoder": lambda v: v or None, "encoder": lambda v: v or ""},
        ),
        (
            "directory",
            "directory",
            {"is_field": True, "decoder": lambda v: v or None, "encoder": lambda v: v or ""},
        ),
        ("client_priority", "priority", {"is_field": True}),
        ("add_paused", "addPaused", {"is_field": True}),
    ]

    @validator("directory")
    def category_directory_mutual_exclusion(
        cls,
        value: Optional[str],
        values: Mapping[str, Any],
    ) -> Optional[str]:
        directory = value
        category: Optional[str] = values.get("category", None)
        if directory and category:
            raise ValueError(
                "'directory' and 'category' are mutually exclusive "
                "on a Transmission/Vuze download client",
            )
        return directory


class TransmissionDownloadClient(TransmissionDownloadClientBase):
    """
    Tramsmission download client.
    """

    type: Literal["transmission"] = "transmission"
    """
    Type value associated with this kind of download client.
    """

    _implementation: str = "Transmission"


class VuzeDownloadClient(TransmissionDownloadClientBase):
    """
    Vuze download client.
    """

    type: Literal["vuze"] = "vuze"
    """
    Type value associated with this kind of download client.
    """

    _implementation: str = "Vuze"


class UtorrentDownloadClient(TorrentDownloadClient):
    """
    uTorrent download client.
    """

    type: Literal["utorrent"] = "utorrent"
    """
    Type value associated with this kind of download client.
    """

    host: NonEmptyStr
    """
    uTorrent host name.
    """

    port: Port = 8080  # type: ignore[assignment]
    """
    Download client access port.
    """

    use_ssl: bool = False
    """
    Use a secure connection when connecting to the download client.
    """

    url_base: Optional[str] = None
    """
    Adds a prefix to the uTorrent URL, e.g. `http://[host]:[port]/[url_base]/api`.
    """

    username: NonEmptyStr
    """
    User name to use when authenticating with the download client.
    """

    password: Password
    """
    Password to use to authenticate the download client user.
    """

    category: Optional[str] = "prowlarr"
    """
    Associate media from Prowlarr with a category.

    Adding a category specific to Prowlarr avoids conflicts with unrelated non-Prowlarr downloads.
    Using a category is optional, but strongly recommended.
    """

    client_priority: UtorrentPriority = UtorrentPriority.last
    """
    Priority to use when grabbing releases.

    Values:

    * `last`
    * `first`
    """

    initial_state: UtorrentState = UtorrentState.start
    """
    Initial state for torrents added to uTorrent.
    """

    category_mappings: Dict[NonEmptyStr, Set[LowerCaseNonEmptyStr]] = {}
    """
    Category mappings for associating a category on the download client
    with the selected Prowlarr categories.
    """

    _implementation: str = "UTorrent"

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
            ("initial_state", "initialState", {"is_field": True}),
            (
                "category_mappings",
                "categories",
                {
                    "decoder": lambda v: cls._category_mappings_decoder(category_ids, v),
                    "encoder": lambda v: cls._category_mappings_encoder(category_ids, v),
                },
            ),
        ]
