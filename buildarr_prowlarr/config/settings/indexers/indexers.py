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
Prowlarr plugin indexers settings configuration.
"""


from __future__ import annotations

from logging import getLogger
from typing import Any, Dict, List, Literal, Mapping, Optional, Set, Tuple, Type, Union

import prowlarr

from buildarr.config import RemoteMapEntry
from buildarr.types import NonEmptyStr, Password
from pydantic import Field, HttpUrl, validator
from typing_extensions import Annotated, Self

from ....api import prowlarr_api_client
from ....secrets import ProwlarrSecrets
from ....types import LowerCaseNonEmptyStr
from ...types import ProwlarrConfigBase

logger = getLogger(__name__)


class Indexer(ProwlarrConfigBase):
    """
    Here is an example of an indexer being configured in the `indexers` configuration
    block in Buildarr.

    ```yaml
    ...
      indexers:
        definitions:
          Nyaa: # Indexer name
            type: "nyaa" # Type of indexer
            # Configuration common to all indexers
            enable_rss: true
            enable_automatic_search: true
            enable_interactive_search: true
            anime_standard_format_search: true
            indexer_priority: 25
            download_client: null
            tags:
              - "example"
            # Nyaa-specific configuration
            website_url: "https://example.com"
          # Define more indexers here.
    ```

    There are configuration parameters common to all indexer types,
    and parameters common to only specific types of indexers.

    The following configuration attributes can be defined on all indexer types.
    """

    site: LowerCaseNonEmptyStr
    """
    The name of the site being accessed by this indexer.

    This is used to determine the defaults for many indexer attributes, such as the
    available indexer base URLs.
    """

    indexer_priority: int = Field(25, ge=1, le=50)
    """
    Priority of this indexer to prefer one indexer over another in release tiebreaker scenarios.

    1 is highest priority and 50 is lowest priority.
    """

    tags: List[NonEmptyStr] = []
    """
    Only use this indexer for series with at least one matching tag.
    Leave blank to use with all series.
    """

    query_limit: Optional[Annotated[int, Field(ge=0)]] = None
    """
    The number of queries within a rolling 24 hour period Prowlarr will allow to the site.

    If empty, undefined or set to `0`, use no limit.
    """

    grab_limit: Optional[Annotated[int, Field(ge=0)]] = None
    """
    The number of grabs within a rolling 24 hour period Prowlarr will allow to the site.

    If empty, undefined or set to `0`, use no limit.
    """

    _implementation_name: str
    _allowed_sites: Set[str] = set()
    _remote_map: List[RemoteMapEntry]

    @validator("site")
    def site_is_allowed(cls, value: str) -> str:
        if cls._allowed_sites and value not in cls._allowed_sites:
            raise ValueError(
                f"must be one of the following allowed sites: {', '.join(cls._allowed_sites)}",
            )
        return value

    @classmethod
    def _get_base_remote_map(cls, tag_ids: Mapping[str, int]) -> List[RemoteMapEntry]:
        return [
            ("indexer_priority", "priority", {}),
            (
                "tags",
                "tags",
                {
                    "decoder": lambda v: [tag for tag, tag_id in tag_ids.items() if tag_id in v],
                    "encoder": lambda v: [tag_ids[tag] for tag in v],
                },
            ),
            ("query_limit", "baseSettings.queryLimit", {"is_field": True}),
            ("grab_limit", "baseSettings.grabLimit", {"is_field": True}),
        ]

    @classmethod
    def _from_remote(cls, tag_ids: Mapping[str, int], remote_attrs: Mapping[str, Any]) -> Self:
        return cls(
            type=cls.__fields__["type"].default,
            **cls.get_local_attrs(
                cls._get_base_remote_map(tag_ids) + cls._remote_map,
                remote_attrs,
            ),
        )

    def _get_schema(self, indexer_schema: List[prowlarr.IndexerResource]) -> Dict[str, Any]:
        return next(s for s in indexer_schema if s.definition_name == self.site).to_dict()

    def _create_remote(
        self,
        tree: str,
        secrets: ProwlarrSecrets,
        tag_ids: Mapping[str, int],
        indexer_schema: List[prowlarr.IndexerResource],
        indexer_name: str,
    ) -> None:
        schema = self._get_schema(indexer_schema)
        changed_attrs = self.get_create_remote_attrs(
            tree,
            self._get_base_remote_map(tag_ids) + self._remote_map,
        )
        changed_fields = {field["name"]: field["value"] for field in changed_attrs["fields"]}
        remote_attrs = {
            **schema,
            **changed_attrs,
            "fields": [
                {**field, "value": changed_fields.get(field["name"], field["value"])}
                for field in schema["fields"]
            ],
        }
        with prowlarr_api_client(secrets=secrets) as api_client:
            prowlarr.IndexerApi(api_client).create_indexer(
                indexer_resource=prowlarr.IndexerResource.from_dict(remote_attrs),
            )

    def _update_remote(
        self,
        tree: str,
        secrets: ProwlarrSecrets,
        remote: Self,
        tag_ids: Mapping[str, int],
        indexer_schema: List[prowlarr.IndexerResource],
        indexer_id: int,
        indexer_name: str,
    ) -> bool:
        updated, changed_attrs = self.get_update_remote_attrs(
            tree,
            remote,
            self._get_base_remote_map(tag_ids) + self._remote_map,
            set_unchanged=True,
        )
        if updated:
            schema = self._get_schema(indexer_schema)
            changed_fields = {field["name"]: field["value"] for field in changed_attrs["fields"]}
            remote_attrs = {
                **schema,
                "id": indexer_id,
                "name": indexer_name,
                **changed_attrs,
                "fields": [
                    {**field, "value": changed_fields.get(field["name"], field["value"])}
                    for field in schema["fields"]
                ],
            }
            with prowlarr_api_client(secrets=secrets) as api_client:
                prowlarr.IndexerApi(api_client).update_indexer(
                    id=str(indexer_id),
                    indexer_resource=prowlarr.IndexerResource.from_dict(remote_attrs),
                )
            return True
        return False

    def _delete_remote(self, tree: str, secrets: ProwlarrSecrets, indexer_id: int) -> None:
        logger.info("%s: (...) -> (deleted)", tree)
        with prowlarr_api_client(secrets=secrets) as api_client:
            prowlarr.IndexerApi(api_client).delete_indexer(id=indexer_id)


class RawIndexer(Indexer):
    """
    Attribute type for defining an indexer of any type.

    This allows users to define indexers of types that Buildarr does not yet explicitly support,
    but almost no validation is done on configured attribute values.

    Buildarr will use the schema for the chosen indexer site as the base for generating API requests
    to Prowlarr, so in most cases it isn't necessary to provide every single possible attribute
    value.

    If any issues are encountered, it is recommended to create the indexer manually on Prowlarr,
    use `buildarr prowlarr dump-config` to dump the indexer configuration, and copy-paste it
    verbatim into the Buildarr configuration to start managing it.
    """

    type: Literal["raw"] = "raw"
    """
    Type value associated with this kind of indexer.
    """

    attributes: Dict[str, Any] = {}

    fields: Dict[str, Any] = {}

    secret_fields: Dict[str, Password] = {}

    _remote_only_attrs: Set[str] = {"added"}

    @validator("secret_fields")
    def check_duplicate_keys(
        cls,
        secret_fields: Dict[str, Password],
        values: Mapping[str, Any],
    ) -> Dict[str, Password]:
        try:
            fields: Dict[str, Any] = values["fields"]
        except KeyError:
            return secret_fields
        for name in set.union(set(secret_fields.keys()), set(fields.keys())):
            if name in fields and name in secret_fields:
                raise ValueError(f"Field '{name}' defined in both 'fields' and 'secret_fields'")
        return secret_fields

    @classmethod
    def _from_remote(cls, tag_ids: Mapping[str, int], remote_attrs: Mapping[str, Any]) -> Self:
        remote_map = cls._get_base_remote_map(tag_ids)
        remote_map_attrs = set(
            entry[1] for entry in remote_map if not entry[2].get("is_field", False)
        )
        remote_map_fields = set(
            (entry[1] for entry in remote_map if entry[2].get("is_field", False)),
        )
        common_attrs = cls.get_local_attrs(remote_map, remote_attrs)
        attributes: Dict[str, Any] = {
            key: value
            for key, value in remote_attrs.items()
            # Attribute to not include in the Buildarr indexer object.
            # These are usually either attributes handled separately
            # (usually common to all indexer types),
            # or automatically generated ones that don't do anything behaviour-wise.
            if key not in ("id", "name", *cls._remote_only_attrs, *remote_map_attrs)
        }
        fields: Dict[str, Any] = {}
        secret_fields: Dict[str, str] = {}
        for field in remote_attrs["fields"]:
            # Do not include 'info' type fields in the Buildarr indexer object,
            # as they are purely informational fields, and only serve to
            # clutter the output.
            if field["type"] == "info":
                continue
            # Ignore fields handled by the `Indexer` base class,
            # which are defined as proper indexer attributes.
            if field["name"] in remote_map_fields:
                continue
            name: str = field["name"]
            lowercase_name = name.lower()
            value: Any = field["value"]
            if isinstance(value, str) and any(
                phrase in lowercase_name for phrase in ("key", "pass")
            ):
                secret_fields[name] = value
            else:
                fields[name] = value
        return cls(
            type=cls.__fields__["type"].default,
            site=remote_attrs["definitionName"],
            **common_attrs,
            attributes=attributes,
            fields=fields,
            secret_fields=secret_fields,
        )

    def _create_remote(
        self,
        tree: str,
        secrets: ProwlarrSecrets,
        tag_ids: Mapping[str, int],
        indexer_schema: List[prowlarr.IndexerResource],
        indexer_name: str,
    ) -> None:
        #
        remote_attrs: Dict[str, Any] = {}
        #
        schema = self._get_schema(indexer_schema)
        #
        remote_map = self._get_base_remote_map(tag_ids)
        remote_map_attrs = set(
            entry[1] for entry in remote_map if not entry[2].get("is_field", False)
        )
        remote_map_fields = set(
            (entry[1] for entry in remote_map if entry[2].get("is_field", False)),
        )
        #
        remote_map_remote_attrs = self.get_create_remote_attrs(
            tree,
            self._get_base_remote_map(tag_ids),
        )
        #
        for key, default_value in schema.items():
            #
            if key == "name":
                remote_attrs[key] = indexer_name
                continue
            #
            if key in self._remote_only_attrs:
                continue
            #
            if key == "fields":
                remote_attrs["fields"] = []
                continue
            #
            if key in remote_map_attrs:
                remote_attrs[key] = remote_map_remote_attrs[key]
                continue
            #
            value = self.attributes.get(key, default_value)
            logger.info(
                "%s.attributes[%s]: %s (created)",
                tree,
                repr(key),
                repr(value),
            )
            remote_attrs[key] = value
        #
        for field in schema["fields"]:
            name = field["name"]
            #
            if name in remote_map_fields:
                for f in remote_map_remote_attrs["fields"]:
                    if f["name"] == name:
                        remote_attrs["fields"].append({**field, "value": f["value"]})
                        break
                else:
                    raise RuntimeError(f"Unable to find field '{name}' in remote map remote attrs")
                continue
            #
            try:
                value = self.secret_fields[name]
                attr_name = "secret_fields"
                format_value = str(value)
                raw_value = value.get_secret_value()
            except KeyError:
                value = self.fields.get(name, field.get("value", None))
                attr_name = "fields"
                format_value = repr(value)
                raw_value = value
            logger.info(
                "%s.%s[%s]: %s (created)",
                tree,
                attr_name,
                repr(name),
                format_value,
            )
            remote_attrs["fields"].append({**field, "value": raw_value})
        #
        with prowlarr_api_client(secrets=secrets) as api_client:
            prowlarr.IndexerApi(api_client).create_indexer(
                indexer_resource=prowlarr.IndexerResource.from_dict(remote_attrs),
            )

    def _update_remote(
        self,
        tree: str,
        secrets: ProwlarrSecrets,
        remote: Self,
        tag_ids: Mapping[str, int],
        indexer_schema: List[prowlarr.IndexerResource],
        indexer_id: int,
        indexer_name: str,
    ) -> bool:
        #
        remote_attrs: Dict[str, Any] = {"id": indexer_id}
        #
        schema = self._get_schema(indexer_schema)
        #
        remote_map = self._get_base_remote_map(tag_ids)
        remote_map_attrs = set(
            entry[1] for entry in remote_map if not entry[2].get("is_field", False)
        )
        remote_map_fields = set(
            (entry[1] for entry in remote_map if entry[2].get("is_field", False)),
        )
        #
        changed, remote_map_remote_attrs = self.get_update_remote_attrs(
            tree,
            remote,
            self._get_base_remote_map(tag_ids),
            set_unchanged=True,
        )
        #
        for key in schema.keys():
            #
            if key == "name":
                remote_attrs[key] = indexer_name
                continue
            #
            if key in self._remote_only_attrs:
                continue
            #
            if key == "fields":
                remote_attrs["fields"] = []
                continue
            #
            if key in remote_map_attrs:
                remote_attrs[key] = remote_map_remote_attrs[key]
                continue
            #
            remote_value = remote.attributes[key]
            try:
                local_value = self.attributes[key]
            except KeyError:
                logger.debug(
                    "%s.attributes[%s]: %s (unmanaged)",
                    tree,
                    repr(key),
                    repr(remote_value),
                )
                remote_attrs[key] = remote_value
            else:
                if local_value != remote_value:
                    logger.info(
                        "%s.attributes[%s]: %s -> %s",
                        tree,
                        repr(key),
                        repr(remote_value),
                        repr(local_value),
                    )
                    remote_attrs[key] = local_value
                    changed = True
                else:
                    logger.debug(
                        "%s.attributes[%s]: %s (up to date)",
                        tree,
                        repr(key),
                        repr(local_value),
                    )
                    remote_attrs[key] = local_value
        #
        for field in schema["fields"]:
            name = field["name"]
            #
            if name in remote_map_fields:
                for f in remote_map_remote_attrs["fields"]:
                    if f["name"] == name:
                        remote_attrs["fields"].append({**field, "value": f["value"]})
                        break
                else:
                    raise RuntimeError(f"Unable to find field '{name}' in remote map remote attrs")
                continue
            #
            if name in self.secret_fields:
                local_value = self.secret_fields[name]
                try:
                    remote_value = remote.secret_fields[name]
                except KeyError:
                    remote_value = Password(remote.fields[name])
                if local_value != remote_value:
                    logger.info(
                        "%s.secret_fields[%s]: %s -> %s",
                        tree,
                        repr(name),
                        str(remote_value),
                        str(local_value),
                    )
                    changed = True
                else:
                    logger.debug(
                        "%s.secret_fields[%s]: %s (up to date)",
                        tree,
                        repr(name),
                        repr(local_value),
                    )
                field_value = local_value.get_secret_value()
            #
            elif name in self.fields:
                local_value = self.fields[name]
                try:
                    remote_value = remote.secret_fields[name].get_secret_value()
                except KeyError:
                    remote_value = remote.fields[name]
                if local_value != remote_value:
                    logger.info(
                        "%s.fields[%s]: %s -> %s",
                        tree,
                        repr(name),
                        repr(remote_value),
                        repr(local_value),
                    )
                    changed = True
                else:
                    logger.debug(
                        "%s.fields[%s]: %s (up to date)",
                        tree,
                        repr(name),
                        repr(local_value),
                    )
                field_value = local_value
            #
            elif name in remote.secret_fields:
                remote_value = remote.secret_fields[name]
                logger.debug(
                    "%s.secret_fields[%s]: %s (unmanaged)",
                    tree,
                    repr(name),
                    str(remote_value),
                )
                field_value = remote_value.get_secret_value()
            #
            else:
                remote_value = remote.fields[name]
                logger.debug(
                    "%s.fields[%s]: %s (unmanaged)",
                    tree,
                    repr(name),
                    repr(remote_value),
                )
                field_value = remote_value
            #
            remote_attrs["fields"].append({**field, "value": field_value})
        #
        if changed:
            with prowlarr_api_client(secrets=secrets) as api_client:
                prowlarr.IndexerApi(api_client).update_indexer(
                    id=str(indexer_id),
                    indexer_resource=prowlarr.IndexerResource.from_dict(remote_attrs),
                )
            return True
        return False


class UsenetIndexer(Indexer):
    """
    Usenet indexer base class.
    """

    pass


class TorrentIndexer(Indexer):
    """
    Configuration attributes common to all torrent indexers.
    """

    seed_ratio: Optional[Annotated[float, Field(ge=0)]] = None
    """
    The ratio a torrent should reach before stopping.

    If empty or undefined, use the app's default.
    """

    seed_time: Optional[Annotated[int, Field(ge=0)]] = None  # minutes
    """
    The time a torrent should be seeded before stopping, in minutes.

    If empty or undefined, use the app's default.
    """

    @classmethod
    def _get_base_remote_map(cls, tag_ids: Mapping[str, int]) -> List[RemoteMapEntry]:
        return [
            *super()._get_base_remote_map(tag_ids),
            ("seed_ratio", "torrentBaseSettings.seedRatio", {"is_field": True}),
            ("seed_time", "torrentBaseSettings.seedTime", {"is_field": True}),
        ]


class AnimebytesIndexer(TorrentIndexer):
    """
    An indexer for monitoring the AnimeBytes private torrent tracker.
    """

    type: Literal["animebytes"] = "animebytes"
    """
    Type value associated with this kind of indexer.
    """

    site: LowerCaseNonEmptyStr = "animebytes"  # type: ignore[assignment]

    base_url: Optional[HttpUrl] = None
    """
    Base URL to use to access the site.

    If undefined, use the default base URL.
    """

    username: NonEmptyStr
    """
    Username to authenticate as.
    """

    passkey: Password
    """
    Passkey to use to authenticate with the site.
    """

    enable_sonarr_compatibility: bool = True
    """
    Makes Prowlarr try to add Season information into Release names.

    Without this Sonarr can't match any Seasons, but it has a lot of false positives as well.
    """

    use_filenames_for_single_episodes: bool = False
    """
    Makes Prowlarr replace AnimeBytes release names with the actual filename.

    This currently only works for single episode releases.
    """

    _implementation_name: str = "AnimeBytes"
    _allowed_sites: Set[str] = {"animebytes"}
    _remote_map: List[RemoteMapEntry] = [
        ("base_url", "baseUrl", {"is_field": True}),
        ("username", "username", {"is_field": True}),
        ("passkey", "passkey", {"is_field": True}),
        ("enable_sonarr_compatibility", "enableSonarrCompatibility", {"is_field": True}),
        ("use_filename_for_single_episodes", "useFilenameForSingleEpisodes", {"is_field": True}),
    ]


class AvistazIndexer(TorrentIndexer):
    """
    An indexer for monitoring the Avistaz private torrent tracker.
    """

    type: Literal["avistaz"] = "avistaz"
    """
    Type value associated with this kind of indexer.
    """

    site: LowerCaseNonEmptyStr = "avistaz"  # type: ignore[assignment]

    base_url: Optional[HttpUrl] = None
    """
    Base URL to use to access the site.

    If undefined, use the default base URL.
    """

    username: NonEmptyStr
    """
    Username to authenticate as.
    """

    password: Password
    """
    Password for the authenticating user.
    """

    pid: Password
    """
    The PID associated with the AvistaZ account.

    Can be retrieved from the from My Account or My Profile page.
    """

    freeleech_only: bool = False
    """
    Search freeleech only.
    """

    _implementation_name: str = "AvistaZ"
    _allowed_sites: Set[str] = {"avistaz"}
    _remote_map: List[RemoteMapEntry] = [
        ("base_url", "baseUrl", {"is_field": True}),
        ("username", "username", {"is_field": True}),
        ("password", "password", {"is_field": True}),
        ("pid", "pid", {"is_field": True}),
        ("freeleech_only", "freeleechOnly", {"is_field": True}),
    ]


class BakabtIndexer(TorrentIndexer):
    """
    An indexer for monitoring the BakaBT anime torrent tracker.
    """

    type: Literal["bakabt"] = "bakabt"
    """
    Type value associated with this kind of indexer.
    """

    site: LowerCaseNonEmptyStr = "bakabt"  # type: ignore[assignment]

    base_url: Optional[HttpUrl] = None
    """
    Base URL to use to access the site.

    If undefined, use the default base URL.
    """

    username: NonEmptyStr
    """
    Username to authenticate as.
    """

    password: Password
    """
    Password for the authenticating user.
    """

    add_romaji_title: bool = True
    """
    Allow releases with titles in
    [rо̄maji](https://en.wikipedia.org/wiki/Romanization_of_Japanese).
    """

    append_season: bool = False
    """
    Append the season, for Sonarr compatibility.
    """

    allow_adult_content: bool = False
    """
    Allow adult content releases.

    This must also be enabled in the BakaBT profile settings.
    """

    _implementation_name: str = "BakaBT"
    _allowed_sites: Set[str] = {"bakabt"}
    _remote_map: List[RemoteMapEntry] = [
        ("base_url", "baseUrl", {"is_field": True}),
        ("username", "username", {"is_field": True}),
        ("password", "password", {"is_field": True}),
        ("add_romaji_title", "addRomajiTitle", {"is_field": True}),
        ("append_season", "appendSeason", {"is_field": True}),
        ("allow_adult_content", "adultContent", {"is_field": True}),
    ]


class BeyondhdIndexer(TorrentIndexer):
    """
    An indexer for monitoring the BeyondHD private torrent tracker for TV shows and movies.
    """

    type: Literal["beyondhd"] = "beyondhd"
    """
    Type value associated with this kind of indexer.
    """

    site: LowerCaseNonEmptyStr = "beyondhd"  # type: ignore[assignment]

    base_url: Optional[HttpUrl] = None
    """
    Base URL to use to access the site.

    If undefined, use the default base URL.
    """

    api_key: Password
    """
    API key used to authenticate with BeyondHD.

    The key can be found in My Security => API Key.
    """

    rss_key: Password
    """
    RSS key used to subscribe to the BeyondHD RSS feed.

    The key can be found in My Security => RSS Key.
    """

    _implementation_name: str = "BeyondHD"
    _allowed_sites: Set[str] = {"beyondhd"}
    _remote_map: List[RemoteMapEntry] = [
        ("base_url", "baseUrl", {"is_field": True}),
        ("api_key", "apiKey", {"is_field": True}),
        ("rss_key", "rssKey", {"is_field": True}),
    ]


class BinsearchIndexer(UsenetIndexer):
    """
    An indexer for monitoring the BinSearch Usenet search engine.
    """

    type: Literal["binsearch"] = "binsearch"
    """
    Type value associated with this kind of indexer.
    """

    site: LowerCaseNonEmptyStr = "binsearch"  # type: ignore[assignment]

    base_url: Optional[HttpUrl] = None
    """
    Base URL to use to access the site.

    If undefined, use the default base URL.
    """

    _implementation_name: str = "BinSearch"
    _allowed_sites: Set[str] = {"binsearch"}
    _remote_map: List[RemoteMapEntry] = [("base_url", "baseUrl", {"is_field": True})]


class BroadcasthenetIndexer(TorrentIndexer):
    """
    Indexer for monitoring the BroacasTheNet private torrent tracker.
    """

    type: Literal["broadcasthenet"] = "broadcasthenet"
    """
    Type value associated with this kind of indexer.
    """

    site: LowerCaseNonEmptyStr = "broadcasthenet"  # type: ignore[assignment]

    base_url: Optional[HttpUrl] = None
    """
    Base URL to use to access the site.

    If undefined, use the default base URL.
    """

    api_key: Password
    """
    BroadcasTheNet API key.
    """

    _implementation_name = "BroadcasTheNet"
    _allowed_sites: Set[str] = {"broadcasthenet"}
    _remote_map: List[RemoteMapEntry] = [
        ("base_url", "baseUrl", {"is_field": True}),
        ("api_key", "apiKey", {"is_field": True}),
    ]


IndexerType = Union[
    RawIndexer,
    AnimebytesIndexer,
    AvistazIndexer,
    BakabtIndexer,
    BeyondhdIndexer,
    BroadcasthenetIndexer,
]

INDEXER_TYPES: Tuple[Type[IndexerType], ...] = (
    # RawIndexer is not included here because it is a special case.
    AnimebytesIndexer,
    AvistazIndexer,
    BakabtIndexer,
    BeyondhdIndexer,
    BroadcasthenetIndexer,
)

INDEXER_TYPE_MAP: Dict[str, Type[IndexerType]] = {
    indexer_type._implementation_name: indexer_type for indexer_type in INDEXER_TYPES
}


class IndexersSettings(ProwlarrConfigBase):
    """
    Indexers are used to monitor for new releases of media on external trackers.
    When a suitable release has been found, Prowlarr registers it for download
    on one of the configured download clients.

    ```yaml
    prowlarr:
      config:
        indexers:
          minimum_age: 0
          retention: 0
          maximum_size: 0
          rss_sync_interval: 15
          delete_unmanaged: false # Better to leave off for the most part
          definitions:
            Nyaa: # Indexer name
              type: "nyaa" # Type of indexer
              # Configuration common to all indexers
              enable_rss: true
              enable_automatic_search: true
              enable_interactive_search: true
              anime_standard_format_search: true
              indexer_priority: 25
              download_client: null
              tags:
                - "example"
              # Nyaa-specific configuration
              website_url: "https://example.com"
            # Define more indexers here.
    ```

    The following parameters are available for configuring indexers and
    how they are handled by Prowlarr.

    For more information on how Prowlarr finds epsiodes, refer to the FAQ on
    [WikiArr](https://wiki.servarr.com/prowlarr/faq#how-does-prowlarr-find-episodes).
    """

    delete_unmanaged: bool = False
    """
    Automatically delete indexers not configured by Buildarr.

    Take care when enabling this option, as it will also delete indexers
    created by external applications such as Prowlarr.

    If unsure, leave set at the default of `false`.
    """

    definitions: Dict[str, Annotated[IndexerType, Field(discriminator="type")]] = {}
    """
    Indexers to manage via Buildarr are defined here.
    """

    @classmethod
    def from_remote(cls, secrets: ProwlarrSecrets) -> Self:
        with prowlarr_api_client(secrets=secrets) as api_client:
            indexers = prowlarr.IndexerApi(api_client).list_indexer()
            tag_ids: Dict[str, int] = (
                {tag.label: tag.id for tag in prowlarr.TagApi(api_client).list_tag()}
                if any(indexer["tags"] for indexer in indexers)
                else {}
            )
        definitions: Dict[str, IndexerType] = {}
        for indexer in indexers:
            try:
                indexer_type: Type[IndexerType] = INDEXER_TYPE_MAP[indexer.implementation_name]
            except KeyError:
                indexer_type = RawIndexer
            definitions[indexer.name] = indexer_type._from_remote(
                tag_ids=tag_ids,
                remote_attrs=indexer.to_dict(),
            )
        return cls(definitions=definitions)

    def update_remote(
        self,
        tree: str,
        secrets: ProwlarrSecrets,
        remote: Self,
        check_unmanaged: bool = False,
    ) -> bool:
        #
        changed = False
        #
        with prowlarr_api_client(secrets=secrets) as api_client:
            indexer_api = prowlarr.IndexerApi(api_client)
            indexer_schema = indexer_api.list_indexer_schema()
            indexer_ids: Dict[str, int] = {
                indexer.name: indexer.id for indexer in indexer_api.list_indexer()
            }
            tag_ids: Dict[str, int] = (
                {tag.label: tag.id for tag in prowlarr.TagApi(api_client).list_tag()}
                if any(indexer.tags for indexer in self.definitions.values())
                or any(indexer.tags for indexer in remote.definitions.values())
                else {}
            )
        #
        for indexer_name, indexer in self.definitions.items():
            indexer_tree = f"{tree}.definitions[{repr(indexer_name)}]"
            #
            if indexer_name not in remote.definitions:
                indexer._create_remote(
                    tree=indexer_tree,
                    secrets=secrets,
                    tag_ids=tag_ids,
                    indexer_schema=indexer_schema,
                    indexer_name=indexer_name,
                )
                changed = True
            #
            elif indexer._update_remote(
                tree=indexer_tree,
                secrets=secrets,
                remote=remote.definitions[indexer_name],  # type: ignore[arg-type]
                tag_ids=tag_ids,
                indexer_schema=indexer_schema,
                indexer_id=indexer_ids[indexer_name],
                indexer_name=indexer_name,
            ):
                changed = True
        #
        for indexer_name, indexer in remote.definitions.items():
            if indexer_name not in self.definitions:
                indexer_tree = f"{tree}.definitions[{repr(indexer_name)}]"
                if self.delete_unmanaged:
                    indexer._delete_remote(
                        tree=indexer_tree,
                        secrets=secrets,
                        indexer_id=indexer_ids[indexer_name],
                    )
                    changed = True
                else:
                    logger.debug("%s: (...) (unmanaged)", indexer_tree)
        #
        return changed
