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

from datetime import datetime
from logging import getLogger
from typing import Any, Dict, List, Mapping, Optional, Set

import prowlarr

from buildarr.config import RemoteMapEntry
from buildarr.types import NonEmptyStr, Password
from pydantic import Field, validator
from typing_extensions import Annotated, Self

from ....api import prowlarr_api_client
from ....secrets import ProwlarrSecrets
from ....types import LowerCaseNonEmptyStr
from ....util import zulu_datetime_format
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

    type: LowerCaseNonEmptyStr
    """
    The name of the site being accessed by this indexer.

    This is used to determine the defaults for many indexer attributes, such as the
    available indexer base URLs.
    """

    enable: bool = False
    """
    When set to `True`, the indexer is active and Prowlarr is making requests to it.
    """

    indexer_priority: int = Field(25, ge=1, le=50)
    """
    Priority of this indexer to prefer one indexer over another in release tiebreaker scenarios.

    1 is highest priority and 50 is lowest priority.
    """

    tags: Set[NonEmptyStr] = set()
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

    fields: Dict[str, Any] = {}

    secret_fields: Dict[str, Password] = {}

    @classmethod
    def _get_base_remote_map(cls, tag_ids: Mapping[str, int]) -> List[RemoteMapEntry]:
        return [
            ("type", "definitionName", {}),
            ("enable", "enable", {}),
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
        remote_map_fields = set(
            (entry[1] for entry in remote_map if entry[2].get("is_field", False)),
        )
        common_attrs = cls.get_local_attrs(remote_map, remote_attrs)
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
            **common_attrs,
            fields=fields,
            secret_fields=secret_fields,
        )

    def _get_schema(self, indexer_schema: List[prowlarr.IndexerResource]) -> Dict[str, Any]:
        return {
            k: v
            for k, v in next(
                s for s in indexer_schema if s.definition_name == self.type
            ).to_dict().items()
            if k not in ["id", "name", "added"]
        }

    def _create_remote(
        self,
        tree: str,
        secrets: ProwlarrSecrets,
        tag_ids: Mapping[str, int],
        indexer_schema: List[prowlarr.IndexerResource],
        indexer_name: str,
    ) -> None:
        #
        schema = self._get_schema(indexer_schema)
        #
        remote_map = self._get_base_remote_map(tag_ids)
        remote_map_fields = set(
            (entry[1] for entry in remote_map if entry[2].get("is_field", False)),
        )
        #
        common_attrs = self.get_create_remote_attrs(tree, remote_map)
        common_fields: List[Dict[str, Any]] = common_attrs["fields"]
        del common_attrs["fields"]
        #
        fields: List[Dict[str, Any]] = []
        for field in schema["fields"]:
            name = field["name"]
            #
            if name in remote_map_fields:
                for f in common_fields:
                    if f["name"] == name:
                        fields.append({**field, "value": f["value"]})
                        break
                else:
                    raise RuntimeError(f"Unable to find field '{name}' in common attrs")
                continue
            #
            try:
                value = self.secret_fields[name]
                attr_name = "secret_fields"
                format_value = str(value)
                raw_value: Any = value.get_secret_value()
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
            fields.append({**field, "value": raw_value})
        #
        with prowlarr_api_client(secrets=secrets) as api_client:
            prowlarr.IndexerApi(api_client).create_indexer(
                indexer_resource=prowlarr.IndexerResource.from_dict(
                    {
                        **schema,
                        "name": indexer_name,
                        **common_attrs,
                        "fields": fields,
                    },
                ),
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
        indexer_added: datetime,
    ) -> bool:
        #
        schema = self._get_schema(indexer_schema)
        #
        remote_map = self._get_base_remote_map(tag_ids)
        remote_map_fields = set(
            (entry[1] for entry in remote_map if entry[2].get("is_field", False)),
        )
        #
        changed, common_attrs = self.get_update_remote_attrs(
            tree,
            remote,
            remote_map,
            set_unchanged=True,
        )
        common_fields: List[Dict[str, Any]] = common_attrs["fields"]
        del common_attrs["fields"]
        #
        fields: List[Dict[str, Any]] = []
        local_value: Any
        remote_value: Any
        for field in schema["fields"]:
            name = field["name"]
            #
            if name in remote_map_fields:
                for f in common_fields:
                    if f["name"] == name:
                        fields.append({**field, "value": f["value"]})
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
            fields.append({**field, "value": field_value})
        #
        if changed:
            with prowlarr_api_client(secrets=secrets) as api_client:
                prowlarr.IndexerApi(api_client).update_indexer(
                    id=str(indexer_id),
                    indexer_resource=prowlarr.IndexerResource.from_dict(
                        {
                            "id": indexer_id,
                            "name": indexer_name,
                            "added": zulu_datetime_format(indexer_added),
                            **schema,
                            **common_attrs,
                            "fields": fields,
                        },
                    ),
                )
            return True
        return False

    def _delete_remote(self, tree: str, secrets: ProwlarrSecrets, indexer_id: int) -> None:
        logger.info("%s: (...) -> (deleted)", tree)
        with prowlarr_api_client(secrets=secrets) as api_client:
            prowlarr.IndexerApi(api_client).delete_indexer(id=indexer_id)


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

    definitions: Dict[str, Indexer] = {}
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
        definitions: Dict[str, Indexer] = {}
        for indexer in indexers:
            definitions[indexer.name] = Indexer._from_remote(
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
            indexer_api_objs: Dict[str, prowlarr.IndexerResource] = {
                indexer.name: indexer for indexer in indexer_api.list_indexer()
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
                indexer_id=indexer_api_objs[indexer_name].id,
                indexer_name=indexer_name,
                indexer_added=indexer_api_objs[indexer_name].added,
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
                        indexer_id=indexer_api_objs[indexer_name].id,
                    )
                    changed = True
                else:
                    logger.debug("%s: (...) (unmanaged)", indexer_tree)
        #
        return changed
