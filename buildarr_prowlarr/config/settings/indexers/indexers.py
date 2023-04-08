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
Prowlarr plugin indexer configuration.
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
    The Prowlarr plugin employs a generic configuration structure for defining indexers,
    where attributes common to all indexer types are individually defined, and
    fields unique to each indexer type are set using Prowlarr's internal representation.

    Below is an example of two indexers being configured in this manner.
    Type-specific configuration attribute are defined under the `fields`
    attribute.

    There is also a `secret_fields` attribute for defining sensitive information
    such as API keys.

    ```yaml
    prowlarr:
      settings:
        indexers:
          indexers:
            definitions:
              "1337x":
                type: "1337x"
                enable: true
                sync_profile: "Standard"
                redirect: false
                priority: 1
                query_limit: 4
                grab_limit: 4
                tags:
                  - "shows"
                fields:
                  "torrentBaseSettings.seedRatio": 3
                  "sort": "created"
                  "type": "desc"
              "Nyaa.si":
                type: "nyaasi"
                enable: true
                sync_profile: "Standard"
                redirect: false
                priority: 1
                query_limit: 4
                grab_limit: 4
                tags:
                  - "anime"
                fields:
                  "torrentBaseSettings.seedRatio": 3
                  "sort": "created"
                  "type": "desc"
                  "cat-id": "All categories"
                  "filter-id": "No filter"
                  "prefer_magnet_links": true
    ```

    Attributes common to all indexer types are documented below.
    """

    type: LowerCaseNonEmptyStr
    """
    The type of indexer to manage. This attribute is unique to each indexer site.
    """

    enable: bool = True
    """
    When set to `True`, the indexer is active and Prowlarr is making requests to it.
    """

    sync_profile: NonEmptyStr
    """
    The application sync profile to use for this indexer.

    [App Sync Profiles](../apps/sync-profiles.md) should be configured before
    using it in an indexer.
    """

    redirect: bool = False
    """
    Redirect incoming download requests for the indexer, and pass the grab directly
    instead of proxying the request via Prowlarr.

    Only supported by some indexer types.
    """

    priority: int = Field(25, ge=1, le=50)
    """
    Priority of this indexer to prefer one indexer over another in release tiebreaker scenarios.

    1 is highest priority and 50 is lowest priority.
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

    tags: Set[NonEmptyStr] = set()
    """
    Tags to associate this indexer with.

    Generally used to associate indexers with applications.
    """

    fields: Dict[str, Any] = {}
    """
    Define configuration attributes unique to each indexer type.

    If an attribute is not defined, its default value is used.
    """

    secret_fields: Dict[str, Password] = {}
    """
    Same as `fields`, but used for string attributes containing sensitive information
    such as API keys.

    Any attributes defined here will have their values hidden in the Buildarr log output.
    """

    @classmethod
    def _get_base_remote_map(
        cls,
        sync_profile_ids: Mapping[str, int],
        tag_ids: Mapping[str, int],
    ) -> List[RemoteMapEntry]:
        return [
            ("type", "definitionName", {}),
            ("enable", "enable", {}),
            (
                "sync_profile",
                "appProfileId",
                {
                    "decoder": lambda v: next(
                        name for name, profile_id in sync_profile_ids.items() if profile_id == v
                    ),
                    "encoder": lambda v: sync_profile_ids[v],
                },
            ),
            ("redirect", "redirect", {}),
            ("priority", "priority", {}),
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
                raise ValueError(f"field '{name}' defined in both 'fields' and 'secret_fields'")
        return secret_fields

    def _get_api_schema(
        self,
        api_indexer_schemas: List[prowlarr.IndexerResource],
    ) -> Dict[str, Any]:
        try:
            return {
                k: v
                for k, v in (
                    next(
                        api_schema
                        for api_schema in api_indexer_schemas
                        if api_schema.definition_name.lower() == self.type.lower()
                    )
                    .to_dict()
                    .items()
                )
                if k not in ["id", "name", "added"]
            }
        except StopIteration:
            expected_types = ", ".join(repr(s.definition_name.lower()) for s in api_indexer_schemas)
            raise ValueError(
                f"Invalid 'type' value for indexer '{self.type}' "
                f"(expected one of: {expected_types})",
            ) from None

    @classmethod
    def _from_remote(
        cls,
        sync_profile_ids: Mapping[str, int],
        tag_ids: Mapping[str, int],
        remote_attrs: Mapping[str, Any],
    ) -> Self:
        # Generate the remote map for reading attribute values.
        remote_map = cls._get_base_remote_map(sync_profile_ids, tag_ids)
        # Create a structure storing the names of all individually-defined
        # attributes that are fields.
        # These are excluded from the dynamically generated `fields`/`secret_fields`
        # structure.
        remote_map_fields = set(
            (entry[1] for entry in remote_map if entry[2].get("is_field", False)),
        )
        # Parse individually-defined attributes from the remote API object.
        common_attrs = cls.get_local_attrs(remote_map, remote_attrs)
        # Parse indexer-specific fields from the remote API object.
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
            # Get the field name and its lowercase variant (for case-insensitive checks).
            name: str = field["name"]
            lowercase_name = name.lower()
            # If the field is of type `select` (an enumeration), instead of
            # exposing the raw values, use the names associated with them
            # to represent the value in the local configuration.
            # If the enumeration uses the indexer URLs instead of defined names,
            # handle that so the URLs are retrieved properly.
            if field["type"] == "select" and field["value"] is not None:
                if field.get("selectOptionsProviderAction", None) == "getUrls":
                    value: Any = remote_attrs["indexerUrls"][field["value"]]
                else:
                    try:
                        value = field["selectOptions"][field["value"]]["name"]
                    except KeyError:
                        value = field["value"]
            else:
                value = field["value"]
            # Add the attribute to `secret_fields` if it looks like
            # a password or key string of some sort.
            # Otherwise, add it to `fields`.
            if field["type"] == "textbox" and any(
                phrase in lowercase_name for phrase in ("key", "pass")
            ):
                secret_fields[name] = value
            else:
                fields[name] = value
        # Construct the local configuration object from the parsed values.
        return cls(
            **common_attrs,
            fields=fields,
            secret_fields=secret_fields,
        )

    def _create_remote(
        self,
        tree: str,
        secrets: ProwlarrSecrets,
        api_indexer_schemas: List[prowlarr.IndexerResource],
        sync_profile_ids: Mapping[str, int],
        tag_ids: Mapping[str, int],
        indexer_name: str,
    ) -> None:
        # Get the API schema for this indexer type.
        # This will supply all the attributes not defined in the indexer object,
        # and ensure the fields are ordered correctly.
        api_schema = self._get_api_schema(api_indexer_schemas)
        # Generate the remote map for encoding local attribute values.
        remote_map = self._get_base_remote_map(sync_profile_ids, tag_ids)
        # Create a structure storing the names of all individually-defined
        # attributes that are fields.
        # These are used to ensure individually defined fields are retrieved
        # from the correct structure when adding them to the outbound API object.
        remote_map_fields = set(
            (entry[1] for entry in remote_map if entry[2].get("is_field", False)),
        )
        # Encode individually-defined attributes from the local configuration.
        # Separate field attributes into a different structure, so they can
        # be combined with the dynamic field attributes.
        common_attrs = self.get_create_remote_attrs(tree, remote_map)
        common_fields: List[Dict[str, Any]] = common_attrs["fields"]
        del common_attrs["fields"]
        # Encode all field attributes into the outbound API object.
        fields: List[Dict[str, Any]] = []
        for field in api_schema["fields"]:
            name = field["name"]
            # Do not include 'info' type fields in the Buildarr indexer object,
            # as they are purely informational fields, and only serve to
            # clutter the output.
            if field["type"] == "info":
                continue
            # If the field is an individually-defined attribute, retrieve the
            # encoded attribute value.
            if name in remote_map_fields:
                for f in common_fields:
                    if f["name"] == name:
                        fields.append({**field, "value": f["value"]})
                        break
                else:
                    raise RuntimeError(f"Unable to find field '{name}' in common attrs")
                continue
            # Retrieve the dynamically generated field value from wherever it was defined
            # (either `fields` or `secret_fields`).
            # If undefined in either, use the default value defined in the API schema.
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
            # If the field type is `select` (an enumeration), encode the enumeration name
            # back into its raw API value case insensitively.
            # If the raw value is already its integer representation, then that means
            # so is the regularly set value and format value: decode them to their
            # string representation.
            if field["type"] == "select" and raw_value is not None:
                if isinstance(raw_value, str):
                    if field.get("selectOptionsProviderAction", None) == "getUrls":
                        raw_value = api_schema["indexerUrls"].index(raw_value)
                    elif "selectOptions" in field:
                        for option in field["selectOptions"]:
                            if option["name"].lower() == raw_value.lower():
                                raw_value = option["value"]
                                break
                        else:
                            raise ValueError(
                                f"Invalid field value '{raw_value}' "
                                "(expected values: "
                                f"{', '.join(repr(f['name']) for f in field['selectOptions'])}"
                                ")",
                            )
                elif field.get("selectOptionsProviderAction", None) == "getUrls":
                    value = api_schema["indexerUrls"][raw_value]
                    format_value = repr(value)
                elif "selectOptions" in field:
                    for option in field["selectOptions"]:
                        if option["value"] == raw_value:
                            value = option["name"]
                            format_value = repr(value)
                            break
                    else:
                        raise ValueError(
                            f"Invalid field select option index {raw_value} "
                            "(expected values: "
                            f"{', '.join(repr(f['value']) for f in field['selectOptions'])}"
                            ")",
                        )
            # Append the field to the outbound API object.
            logger.info(
                "%s.%s[%s]: %s (created)",
                tree,
                attr_name,
                repr(name),
                format_value,
            )
            fields.append({**field, "value": raw_value})
        # Send the create request to the remote instance.
        with prowlarr_api_client(secrets=secrets) as api_client:
            prowlarr.IndexerApi(api_client).create_indexer(
                indexer_resource=prowlarr.IndexerResource.from_dict(
                    {
                        **api_schema,
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
        api_indexer_schemas: List[prowlarr.IndexerResource],
        sync_profile_ids: Mapping[str, int],
        tag_ids: Mapping[str, int],
        indexer_id: int,
        indexer_name: str,
        indexer_added: datetime,
    ) -> bool:
        # Get the API schema for this indexer type.
        # This will ensure the fields are ordered correctly.
        api_schema = self._get_api_schema(api_indexer_schemas)
        # Generate the remote map for encoding local attribute values.
        remote_map = self._get_base_remote_map(sync_profile_ids, tag_ids)
        # Create a structure storing the names of all individually-defined
        # attributes that are fields.
        # These are used to ensure individually defined fields are retrieved
        # from the correct structure when adding them to the outbound API object.
        remote_map_fields = set(
            (entry[1] for entry in remote_map if entry[2].get("is_field", False)),
        )
        # Encode individually-defined attributes that are different
        # between the local and remote configuration.
        # Separate field attributes into a different structure, so they can
        # be combined with the dynamic field attributes.
        changed, common_attrs = self.get_update_remote_attrs(
            tree,
            remote,
            remote_map,
            set_unchanged=True,
        )
        common_fields: List[Dict[str, Any]] = common_attrs["fields"]
        del common_attrs["fields"]
        # Encode all field attributes into the outbound API object.
        fields: List[Dict[str, Any]] = []
        local_value: Any
        remote_value: Any
        for field in api_schema["fields"]:
            name = field["name"]
            case_insensitive = False
            # Do not include 'info' type fields in the Buildarr indexer object,
            # as they are purely informational fields, and only serve to
            # clutter the output.
            if field["type"] == "info":
                continue
            # If the field is an individually-defined attribute, retrieve the
            # encoded attribute value.
            if name in remote_map_fields:
                for f in common_fields:
                    if f["name"] == name:
                        fields.append({**field, "value": f["value"]})
                        break
                else:
                    raise RuntimeError(f"Unable to find field '{name}' in remote map remote attrs")
                continue
            # Retrieve the local and remote dynamically generated field values
            # from wherever they were defined (either `fields` or `secret_fields`).
            if name in self.secret_fields:
                attr_name = "secrets_fields"
                local_value = self.secret_fields[name]
                try:
                    remote_value = remote.secret_fields[name]
                except KeyError:
                    remote_value = Password(remote.fields[name])
                local_formatted_value = repr(str(local_value))
                remote_formatted_value = repr(str(remote_value))
                local_raw_value = local_value.get_secret_value()
                remote_raw_value = remote_value.get_secret_value()
            else:
                attr_name = "fields"
                try:
                    remote_value = remote.secret_fields[name].get_secret_value()
                except KeyError:
                    remote_value = remote.fields[name]
                local_value = self.fields.get(name, remote_value)
                local_formatted_value = repr(local_value)
                remote_formatted_value = repr(remote_value)
                local_raw_value = local_value
                remote_raw_value = remote_value
            # If the field type is `select` (an enumeration), encode the enumeration name
            # back into its raw API value case insensitively, for both local and remote values.
            if field["type"] == "select" and field["value"] is not None:
                if field.get("selectOptionsProviderAction", None) == "getUrls":
                    local_raw_value = api_schema["indexerUrls"].index(local_raw_value)
                    remote_raw_value = api_schema["indexerUrls"].index(remote_raw_value)
                elif "selectOptions" in field:
                    case_insensitive = True
                    for option in field["selectOptions"]:
                        if option["name"].lower() == local_raw_value.lower():
                            local_raw_value = option["value"]
                            break
                    else:
                        raise ValueError(
                            f"Invalid local field value '{local_raw_value}' "
                            "(expected values: "
                            f"{', '.join(repr(f['name']) for f in field['selectOptions'])}"
                            ")",
                        )
                    for option in field["selectOptions"]:
                        if option["name"].lower() == remote_raw_value.lower():
                            remote_raw_value = option["value"]
                            break
                    else:
                        raise RuntimeError(
                            f"Invalid remote field value '{local_raw_value}' "
                            "(expected values: "
                            f"{', '.join(repr(f['name']) for f in field['selectOptions'])}"
                            ")",
                        )
            # Compare the local value to the remote value for this
            # dynamic field attribute, and set the flag for updating
            # the remote instance if they are different.
            if case_insensitive:
                value_changed = local_value.lower() != remote_value.lower()
            else:
                value_changed = local_value != remote_value
            if value_changed:
                logger.info(
                    "%s.%s[%s]: %s -> %s",
                    tree,
                    attr_name,
                    repr(name),
                    remote_formatted_value,
                    local_formatted_value,
                )
                raw_value = local_raw_value
                changed = True
            else:
                logger.debug(
                    "%s.%s[%s]: %s (%s)",
                    tree,
                    attr_name,
                    repr(name),
                    remote_formatted_value,
                    (
                        "up to date"
                        if name in self.fields or name in self.secret_fields
                        else "unmanaged"
                    ),
                )
                raw_value = remote_raw_value
            # Append the field to the outbound API object.
            fields.append({**field, "value": raw_value})
        # Send the update request to the remote instance, if required.
        if changed:
            with prowlarr_api_client(secrets=secrets) as api_client:
                prowlarr.IndexerApi(api_client).update_indexer(
                    id=str(indexer_id),
                    indexer_resource=prowlarr.IndexerResource.from_dict(
                        {
                            "id": indexer_id,
                            "name": indexer_name,
                            "added": zulu_datetime_format(indexer_added),
                            **api_schema,
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

    Prowlarr acts as a proxy for configured indexer sites. Configured applications
    will subscribe to Prowlarr, which will perform searches on the applications'
    behalf, and return the results.

    The applications will then decide whether or not to fetch the release, and if so,
    schedule grabs with their own configured download clients.

    For more information on correctly setting up Prowlarr indexers, refer to the
    [Prowlarr indexers configuration guide](https://wiki.servarr.com/prowlarr/indexers) on WikiArr.

    In Buildarr, Prowlarr indexers are configured under the following structure:

    ```yaml
    prowlarr:
      settings:
        indexers:
          indexers:
            delete_unmanaged: false  # Do not delete indexers not setup by Buildarr by default.
            definitions:
              "Indexer1":
                type: nyaasi
                ...
              "Indexer2":
                type: 1337x
                ...
    ```
    """

    delete_unmanaged: bool = False
    """
    Automatically delete indexers not configured by Buildarr.

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
            sync_profile_ids: Dict[str, int] = {
                profile.name: profile.id
                for profile in prowlarr.AppProfileApi(api_client).list_app_profile()
            }
            tag_ids: Dict[str, int] = (
                {tag.label: tag.id for tag in prowlarr.TagApi(api_client).list_tag()}
                if any(indexer["tags"] for indexer in indexers)
                else {}
            )
        definitions: Dict[str, Indexer] = {}
        for indexer in indexers:
            definitions[indexer.name] = Indexer._from_remote(
                sync_profile_ids=sync_profile_ids,
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
        # Track whether or not any changes have been made on the remote instance.
        changed = False
        # Pull API objects and metadata required during the update operation.
        with prowlarr_api_client(secrets=secrets) as api_client:
            indexer_api = prowlarr.IndexerApi(api_client)
            api_indexer_schemas = indexer_api.list_indexer_schema()
            indexer_api_objs: Dict[str, prowlarr.IndexerResource] = {
                indexer.name: indexer for indexer in indexer_api.list_indexer()
            }
            sync_profile_ids: Dict[str, int] = {
                profile.name: profile.id
                for profile in prowlarr.AppProfileApi(api_client).list_app_profile()
            }
            tag_ids: Dict[str, int] = (
                {tag.label: tag.id for tag in prowlarr.TagApi(api_client).list_tag()}
                if any(indexer.tags for indexer in self.definitions.values())
                or any(indexer.tags for indexer in remote.definitions.values())
                else {}
            )
        # Compare local definitions to their remote equivalent.
        # If a local definition does not exist on the remote, create it.
        # If it does exist on the remote, attempt an an in-place modification,
        # and set the `changed` flag if modifications were made.
        for indexer_name, indexer in self.definitions.items():
            indexer_tree = f"{tree}.definitions[{repr(indexer_name)}]"
            if indexer_name not in remote.definitions:
                indexer._create_remote(
                    tree=indexer_tree,
                    secrets=secrets,
                    api_indexer_schemas=api_indexer_schemas,
                    sync_profile_ids=sync_profile_ids,
                    tag_ids=tag_ids,
                    indexer_name=indexer_name,
                )
                changed = True
            elif indexer._update_remote(
                tree=indexer_tree,
                secrets=secrets,
                remote=remote.definitions[indexer_name],  # type: ignore[arg-type]
                api_indexer_schemas=api_indexer_schemas,
                sync_profile_ids=sync_profile_ids,
                tag_ids=tag_ids,
                indexer_id=indexer_api_objs[indexer_name].id,
                indexer_name=indexer_name,
                indexer_added=indexer_api_objs[indexer_name].added,
            ):
                changed = True
        # Traverse the remote definitions, and see if there are any remote definitions
        # that do not exist in the local configuration.
        # If `delete_unmanaged` is enabled, delete it from the remote.
        # If `delete_unmanaged` is disabled, just add a log entry acknowledging
        # the existence of the unmanaged definition.
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
        # Return whether or not the remote instance was changed.
        return changed
