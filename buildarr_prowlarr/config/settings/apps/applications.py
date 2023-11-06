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
Prowlarr plugin application link settings configuration.
"""


from __future__ import annotations

from logging import getLogger
from typing import Any, Dict, Iterable, List, Literal, Mapping, Optional, Set, Union, cast

import prowlarr

from buildarr.config import RemoteMapEntry
from buildarr.state import state
from buildarr.types import BaseEnum, InstanceName, NonEmptyStr, Password
from pydantic import AnyHttpUrl, Field, SecretStr, validator
from typing_extensions import Annotated, Self

from ....api import prowlarr_api_client
from ....secrets import ProwlarrSecrets
from ....types import ArrApiKey, LowerCaseNonEmptyStr
from ...types import ProwlarrConfigBase

logger = getLogger(__name__)


class SyncLevel(BaseEnum):
    disabled = "disabled"
    add_and_remove_only = "addOnly"
    full_sync = "fullSync"


class Application(ProwlarrConfigBase):
    """
    Prowlarr application links have the following common configuration attributes.
    """

    type: str
    """
    Type value associated with this kind of connection.
    """

    prowlarr_url: AnyHttpUrl
    """
    Prowlarr server URL as the target application sees it,
    including `http[s]://`, port, and URL base (if needed).

    This attribute is required, even for applications with instance links.
    """

    base_url: AnyHttpUrl
    """
    URL that Prowlarr uses to connect to the target application server,
    including `http[s]://`, port, and URL base (if needed).

    This attribute is required, even for applications with instance links.
    """

    sync_level: SyncLevel = SyncLevel.add_and_remove_only
    """
    Configures when Prowlarr will sync indexer configuration with the application.

    Values:

    * `disable` (Do not sync indexers with the application)
    * `add-and-remove-only` (Sync when indexers are added or removed)
    * `full-sync` (Sync all indexer changes to the application)
    """

    sync_categories: Set[LowerCaseNonEmptyStr]
    """
    Categories of content to sync with the target application.

    Each type of application has individually set default values.

    Note that only categories supported by the application will actually be used.
    """

    tags: Set[NonEmptyStr] = set()
    """
    Prowlarr tags to assign to this application.

    This is used to associate the application with indexers.
    """

    _implementation: str
    _remote_map: List[RemoteMapEntry] = []

    @classmethod
    def _get_base_remote_map(
        cls,
        api_schema: prowlarr.ApplicationResource,
        tag_ids: Mapping[str, int],
    ) -> List[RemoteMapEntry]:
        return [
            ("prowlarr_url", "prowlarrUrl", {"is_field": True}),
            ("base_url", "baseUrl", {"is_field": True}),
            ("sync_level", "syncLevel", {}),
            (
                "sync_categories",
                "syncCategories",
                {
                    "is_field": True,
                    "decoder": lambda v: cls._sync_categories_decoder(api_schema, v),
                    "encoder": lambda v: cls._sync_categories_encoder(api_schema, v),
                },
            ),
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
    def _get_sync_category_options(
        cls,
        api_schema: prowlarr.ApplicationResource,
    ) -> Dict[int, str]:
        return {
            select_option.value: select_option.name.lower()
            for select_option in cast(
                List[prowlarr.SelectOption],
                next(
                    (
                        f
                        for f in cast(List[prowlarr.Field], api_schema.fields)
                        if f.name == "syncCategories"
                    ),
                ).select_options,
            )
        }

    @classmethod
    def _sync_categories_decoder(
        cls,
        api_schema: prowlarr.ApplicationResource,
        api_sync_categories: Iterable[int],
    ) -> Set[str]:
        category_names = cls._get_sync_category_options(api_schema)
        return set(category_names[category_id] for category_id in api_sync_categories)

    @classmethod
    def _sync_categories_encoder(
        cls,
        api_schema: prowlarr.ApplicationResource,
        sync_categories: Set[str],
    ) -> List[int]:
        category_ids = {v: k for k, v in cls._get_sync_category_options(api_schema).items()}
        return sorted(category_ids[category_name] for category_name in sync_categories)

    @classmethod
    def _from_remote(
        cls,
        api_schema: prowlarr.ApplicationResource,
        tag_ids: Mapping[str, int],
        remote_attrs: Mapping[str, Any],
    ) -> Self:
        return cls(
            **cls.get_local_attrs(
                remote_map=cls._get_base_remote_map(api_schema, tag_ids) + cls._remote_map,
                remote_attrs=remote_attrs,
            ),
        )

    def _resolve(self) -> Self:
        return self

    def _create_remote(
        self,
        tree: str,
        secrets: ProwlarrSecrets,
        api_schema: prowlarr.ApplicationResource,
        tag_ids: Mapping[str, int],
        application_name: str,
    ) -> None:
        api_schema_dict = api_schema.to_dict()
        set_attrs = self.get_create_remote_attrs(
            tree=tree,
            remote_map=self._get_base_remote_map(api_schema, tag_ids) + self._remote_map,
        )
        field_values: Dict[str, Any] = {
            field["name"]: field["value"] for field in set_attrs["fields"]
        }
        set_attrs["fields"] = [
            ({**f, "value": field_values[f["name"]]} if f["name"] in field_values else f)
            for f in api_schema_dict["fields"]
        ]
        remote_attrs = {**api_schema_dict, "name": application_name, **set_attrs}
        with prowlarr_api_client(secrets=secrets) as api_client:
            prowlarr.ApplicationApi(api_client).create_applications(
                application_resource=prowlarr.ApplicationResource.from_dict(remote_attrs),
            )

    def _update_remote(
        self,
        tree: str,
        secrets: ProwlarrSecrets,
        remote: Self,
        api_schema: prowlarr.ApplicationResource,
        tag_ids: Mapping[str, int],
        api_application: prowlarr.ApplicationResource,
    ) -> bool:
        changed, set_attrs = self.get_update_remote_attrs(
            tree=tree,
            remote=remote,
            remote_map=self._get_base_remote_map(api_schema, tag_ids) + self._remote_map,
            set_unchanged=True,
        )
        if changed:
            if "fields" in set_attrs:
                field_values: Dict[str, Any] = {
                    field["name"]: field["value"] for field in set_attrs["fields"]
                }
                set_attrs["fields"] = [
                    {**f, "value": field_values[f["name"]]} for f in api_schema.to_dict()["fields"]
                ]
            remote_attrs = {**api_application.to_dict(), **set_attrs}
            with prowlarr_api_client(secrets=secrets) as api_client:
                prowlarr.ApplicationApi(api_client).update_applications(
                    id=str(api_application.id),
                    application_resource=prowlarr.ApplicationResource.from_dict(remote_attrs),
                )
            return True
        return False

    def _delete_remote(self, secrets: ProwlarrSecrets, application_id: int) -> None:
        with prowlarr_api_client(secrets=secrets) as api_client:
            prowlarr.ApplicationApi(api_client).delete_applications(id=application_id)


class LazylibrarianApplication(Application):
    """
    Add a [LazyLibrarian](https://lazylibrarian.gitlab.io) instance to sync with Prowlarr.
    """

    type: Literal["lazylibrarian", "lazylibrary"] = "lazylibrarian"
    """
    Type value associated with this kind of application.
    """

    api_key: Password
    """
    API key used to access the target instance.
    """

    sync_categories: Set[LowerCaseNonEmptyStr] = {
        "Books/Mags",  # type: ignore[arg-type]
        "Books/EBook",  # type: ignore[arg-type]
        "Books/Comics",  # type: ignore[arg-type]
        "Books/Technical",  # type: ignore[arg-type]
        "Books/Other",  # type: ignore[arg-type]
        "Books/Foreign",  # type: ignore[arg-type]
    }
    """
    Default sync category values for this application type.
    """

    _implementation: str = "LazyLibrarian"
    _remote_map: List[RemoteMapEntry] = [("api_key", "apiKey", {"is_field": True})]


class LidarrApplication(Application):
    """
    Add a [Lidarr](https://lidarr.audio) instance to sync with Prowlarr.
    """

    type: Literal["lidarr"] = "lidarr"
    """
    Type value associated with this kind of application.
    """

    api_key: ArrApiKey
    """
    API key used to access the target instance.
    """

    sync_categories: Set[LowerCaseNonEmptyStr] = {
        "Audio/MP3",  # type: ignore[arg-type]
        "Audio/Audiobook",  # type: ignore[arg-type]
        "Audio/Lossless",  # type: ignore[arg-type]
        "Audio/Other",  # type: ignore[arg-type]
        "Audio/Foreign",  # type: ignore[arg-type]
    }
    """
    Default sync category values for this application type.
    """

    _implementation: str = "Lidarr"
    _remote_map: List[RemoteMapEntry] = [("api_key", "apiKey", {"is_field": True})]


class MylarApplication(Application):
    """
    Add a [Mylar](https://github.com/mylar3/mylar3) instance to sync with Prowlarr.
    """

    type: Literal["mylar"] = "mylar"
    """
    Type value associated with this kind of application.
    """

    api_key: Password
    """
    API key used to access the target instance.
    """

    sync_categories: Set[LowerCaseNonEmptyStr] = {"Books/Comics"}  # type: ignore[arg-type]
    """
    Default sync category values for this application type.
    """

    _implementation: str = "Mylar"
    _remote_map: List[RemoteMapEntry] = [("api_key", "apiKey", {"is_field": True})]


class RadarrApplication(Application):
    """
    Add a [Radarr](https://radarr.video) instance to sync with Prowlarr.

    !!! note

        There is a [Radarr plugin for Buildarr](https://buidarr.github.io/plugins/radarr)
        that can be used to link Radarr instances with Prowlarr using the `instance_name`
        attribute.
    """

    type: Literal["radarr"] = "radarr"
    """
    Type value associated with this kind of application.
    """

    instance_name: Optional[InstanceName] = Field(None, plugin="radarr")
    """
    The name of the Radarr instance within Buildarr, if adding
    a Buildarr-defined Radarr instance to this Prowlarr instance.
    """

    api_key: Optional[ArrApiKey] = None
    """
    API key used to access the target Radarr instance.

    If a Radarr instance managed by Buildarr is not referenced using `instance_name`,
    this attribute is required.
    """

    sync_categories: Set[LowerCaseNonEmptyStr] = {
        "Movies/Foreign",  # type: ignore[arg-type]
        "Movies/Other",  # type: ignore[arg-type]
        "Movies/SD",  # type: ignore[arg-type]
        "Movies/HD",  # type: ignore[arg-type]
        "Movies/UHD",  # type: ignore[arg-type]
        "Movies/BluRay",  # type: ignore[arg-type]
        "Movies/3D",  # type: ignore[arg-type]
        "Movies/DVD",  # type: ignore[arg-type]
        "Movies/WEB-DL",  # type: ignore[arg-type]
    }
    """
    Default sync category values for this application type.
    """

    _implementation: str = "Radarr"
    _remote_map: List[RemoteMapEntry] = [("api_key", "apiKey", {"is_field": True})]

    @validator("api_key")
    def validate_api_key(
        cls,
        value: Optional[SecretStr],
        values: Dict[str, Any],
    ) -> Optional[SecretStr]:
        if not values.get("instance_name", None) and not value:
            raise ValueError("required when 'instance_name' is not defined")
        return value

    def _resolve(self) -> Self:
        if self.instance_name:
            resolved = self.copy(deep=True)
            resolved.api_key = state.secrets.radarr[  # type: ignore[attr-defined]
                self.instance_name
            ].api_key.get_secret_value()
            return resolved
        return self


class ReadarrApplication(Application):
    """
    Add a [Readarr](https://readarr.com) instance to sync with Prowlarr.
    """

    type: Literal["readarr"] = "readarr"
    """
    Type value associated with this kind of application.
    """

    api_key: ArrApiKey
    """
    API key used to access the target instance.
    """

    sync_categories: Set[LowerCaseNonEmptyStr] = {
        "Audio/Audiobook",  # type: ignore[arg-type]
        "Books/Mags",  # type: ignore[arg-type]
        "Books/EBook",  # type: ignore[arg-type]
        "Books/Comics",  # type: ignore[arg-type]
        "Books/Technical",  # type: ignore[arg-type]
        "Books/Other",  # type: ignore[arg-type]
        "Books/Foreign",  # type: ignore[arg-type]
    }
    """
    Default sync category values for this application type.
    """

    _implementation: str = "Readarr"
    _remote_map: List[RemoteMapEntry] = [("api_key", "apiKey", {"is_field": True})]


class SonarrApplication(Application):
    """
    Add a [Sonarr](https://sonarr.tv) instance to sync with Prowlarr.

    !!! note

        There is a [Sonarr plugin for Buildarr](https://buidarr.github.io/plugins/sonarr)
        that can be used to link Sonarr instances with Prowlarr using the `instance_name`
        attribute.
    """

    type: Literal["sonarr"] = "sonarr"
    """
    Type value associated with this kind of application.
    """

    instance_name: Optional[InstanceName] = Field(None, plugin="sonarr")
    """
    The name of the Sonarr instance within Buildarr, if adding
    a Buildarr-defined Sonarr instance to this Prowlarr instance.
    """

    api_key: Optional[ArrApiKey] = None
    """
    API key used to access the target Sonarr instance.

    If a Sonarr instance managed by Buildarr is not referenced using `instance_name`,
    this attribute is required.
    """

    sync_categories: Set[LowerCaseNonEmptyStr] = {
        "TV/WEB-DL",  # type: ignore[arg-type]
        "TV/Foreign",  # type: ignore[arg-type]
        "TV/SD",  # type: ignore[arg-type]
        "TV/HD",  # type: ignore[arg-type]
        "TV/UHD",  # type: ignore[arg-type]
        "TV/Other",  # type: ignore[arg-type]
    }
    """
    Default sync category values for this application type.
    """

    anime_sync_categories: Set[LowerCaseNonEmptyStr] = {"TV/Anime"}  # type: ignore[arg-type]
    """
    Categories of content for sync with the target application, classified as anime.

    Note that only categories supported by the application will actually be used.
    """

    sync_anime_standard_format_search: bool = False
    """
    Enable searching using anime standard episode numbering for the Sonarr instance.

    *New in version 0.4.0.*
    """

    _implementation: str = "Sonarr"

    @validator("api_key")
    def validate_api_key(
        cls,
        value: Optional[SecretStr],
        values: Dict[str, Any],
    ) -> Optional[SecretStr]:
        if not values.get("instance_name", None) and not value:
            raise ValueError("required when 'instance_name' is not defined")
        return value

    @classmethod
    def _get_base_remote_map(
        cls,
        api_schema: prowlarr.ApplicationResource,
        tag_ids: Mapping[str, int],
    ) -> List[RemoteMapEntry]:
        return [
            *super()._get_base_remote_map(api_schema, tag_ids),
            ("api_key", "apiKey", {"is_field": True}),
            (
                "anime_sync_categories",
                "animeSyncCategories",
                {
                    "is_field": True,
                    "decoder": lambda v: cls._sync_categories_decoder(api_schema, v),
                    "encoder": lambda v: cls._sync_categories_encoder(api_schema, v),
                },
            ),
            (
                "sync_anime_standard_format_search",
                "syncAnimeStandardFormatSearch",
                {"is_field": True},
            ),
        ]

    def _resolve(self) -> Self:
        if self.instance_name:
            resolved = self.copy(deep=True)
            resolved.api_key = state.secrets.sonarr[  # type: ignore[attr-defined]
                self.instance_name
            ].api_key.get_secret_value()
            return resolved
        return self


class WhisparrApplication(Application):
    """
    Add a [Whisparr](https://github.com/Whisparr/Whisparr) instance to sync with Prowlarr.
    """

    type: Literal["whisparr"] = "whisparr"
    """
    Type value associated with this kind of application.
    """

    api_key: ArrApiKey
    """
    API key used to access the target instance.
    """

    sync_categories: Set[LowerCaseNonEmptyStr] = {
        "XXX/DVD",  # type: ignore[arg-type]
        "XXX/WMV",  # type: ignore[arg-type]
        "XXX/XviD",  # type: ignore[arg-type]
        "XXX/x264",  # type: ignore[arg-type]
        "XXX/Pack",  # type: ignore[arg-type]
        "XXX/Other",  # type: ignore[arg-type]
        "XXX/SD",  # type: ignore[arg-type]
        "XXX/WEB-DL",  # type: ignore[arg-type]
    }
    """
    Default sync category values for this application type.
    """

    _implementation: str = "Whisparr"
    _remote_map: List[RemoteMapEntry] = [("api_key", "apiKey", {"is_field": True})]


APPLICATION_TYPE_MAP = {
    application_type._implementation: application_type  # type: ignore[attr-defined]
    for application_type in (
        LazylibrarianApplication,
        LidarrApplication,
        MylarApplication,
        RadarrApplication,
        ReadarrApplication,
        SonarrApplication,
        WhisparrApplication,
    )
}

ApplicationType = Union[
    LazylibrarianApplication,
    LidarrApplication,
    MylarApplication,
    RadarrApplication,
    ReadarrApplication,
    SonarrApplication,
    WhisparrApplication,
]


class ApplicationsSettings(ProwlarrConfigBase):
    """
    Prowlarr syncs indexer configuration with connected applications, and performs requests
    to the indexer on the application's behalf.

    Buildarr makes configuring these applications easier through instance links.

    By installing the Buildarr plugin for the application (e.g. Sonarr)
    alongside the Prowlarr plugin, you can manage the instances using a single Buildarr
    instance, and link them together so that you don't need to supply certain parameters
    multiple times, e.g. the API key.

    Buildarr will also intelligently manage updates so that the connected application
    instance is updated before the Prowlarr instance, to ensure state is consistent
    at each update stage.

    ```yaml
    ---

    sonarr:
      instances:
        "Sonarr": {}  # Define instance configuration.

    prowlarr:
      settings:
        apps:
          applications:
            definitions:
              "Sonarr":
                type: "sonarr"
                instance_name: "Sonarr"
                prowlarr_url: "http://prowlarr:9696"
                base_url: "http://sonarr:8989"
                tags:
                  - "anime"
    ```

    If the application does not have a Buildarr plugin, they can also be configured
    without instance links by supplying the required parameters.

    ```yaml
    prowlarr:
      settings:
        apps:
          applications:
            definitions:
              "Radarr":
                type: "radarr"
                api_key: "1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d"
                prowlarr_url: "http://prowlarr:9696"
                base_url: "http://radarr:7878"
                sync_level: "add-and-remove-only"
                sync_categories:
                  - "Movies/UHD"
                  - "Movies/HD"
                  - "Movies/SD"
                  - "Movies/3D"
                  - "Movies/BluRay"
                  - "Movies/DVD"
                  - "Movies/WEB-DL"
                  - "Movies/Foreign"
                  - "Movies/Other"
                tags:
                  - "movies"
    ```

    For more information on configuring application links in Prowlarr,
    refer to the [guide for applications](https://wiki.servarr.com/prowlarr/settings#applications)
    on WikiArr.
    """

    delete_unmanaged: bool = False
    """
    Automatically delete application links not configured in Buildarr.

    Take care when enabling this option, as this can remove connections automatically
    managed by other applications.
    """

    definitions: Dict[str, Annotated[ApplicationType, Field(discriminator="type")]] = {}
    """
    Application link definitions to configure in Prowlarr.
    """

    @classmethod
    def from_remote(cls, secrets: ProwlarrSecrets) -> Self:
        with prowlarr_api_client(secrets=secrets) as api_client:
            application_api = prowlarr.ApplicationApi(api_client)
            api_application_schemas: Dict[str, prowlarr.ApplicationResource] = {
                api_schema.implementation: api_schema
                for api_schema in application_api.list_applications_schema()
            }
            api_applications = application_api.list_applications()
            tag_ids: Dict[str, int] = (
                {tag.label: tag.id for tag in prowlarr.TagApi(api_client).list_tag()}
                if any(api_application.tags for api_application in api_applications)
                else {}
            )
        return cls(
            definitions={
                api_application.name: APPLICATION_TYPE_MAP[  # type: ignore[attr-defined]
                    api_application.implementation
                ]._from_remote(
                    api_schema=api_application_schemas[api_application.implementation],
                    tag_ids=tag_ids,
                    remote_attrs=api_application.to_dict(),
                )
                for api_application in api_applications
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
            application_api = prowlarr.ApplicationApi(api_client)
            api_application_schemas: Dict[str, prowlarr.ApplicationResource] = {
                api_schema.implementation: api_schema
                for api_schema in application_api.list_applications_schema()
            }
            api_applications = {
                api_application.name: api_application
                for api_application in application_api.list_applications()
            }
            tag_ids: Dict[str, int] = (
                {tag.label: tag.id for tag in prowlarr.TagApi(api_client).list_tag()}
                if any(application.tags for application in self.definitions.values())
                or any(application.tags for application in remote.definitions.values())
                else {}
            )
        # Compare local definitions to their remote equivalent.
        # If a local definition does not exist on the remote, create it.
        # If it does exist on the remote, attempt an an in-place modification,
        # and set the `changed` flag if modifications were made.
        for application_name, application in self.definitions.items():
            application_tree = f"{tree}.definitions[{application_name!r}]"
            local_application = application._resolve()
            if application_name not in remote.definitions:
                local_application._create_remote(
                    tree=application_tree,
                    secrets=secrets,
                    api_schema=api_application_schemas[application._implementation],
                    tag_ids=tag_ids,
                    application_name=application_name,
                )
                changed = True
            elif local_application._update_remote(
                tree=application_tree,
                secrets=secrets,
                remote=remote.definitions[application_name],  # type: ignore[arg-type]
                api_schema=api_application_schemas[application._implementation],
                tag_ids=tag_ids,
                api_application=api_applications[application_name],
            ):
                changed = True
        # Return whether or not the remote instance was changed.
        return changed

    def delete_remote(self, tree: str, secrets: ProwlarrSecrets, remote: Self) -> bool:
        # Track whether or not any changes have been made on the remote instance.
        changed = False
        # Pull API objects and metadata required during the update operation.
        with prowlarr_api_client(secrets=secrets) as api_client:
            application_ids: Dict[str, int] = {
                api_application.name: api_application.id
                for api_application in prowlarr.ApplicationApi(api_client).list_applications()
            }
        # Traverse the remote definitions, and see if there are any remote definitions
        # that do not exist in the local configuration.
        # If `delete_unmanaged` is enabled, delete it from the remote.
        # If `delete_unmanaged` is disabled, just add a log entry acknowledging
        # the existence of the unmanaged definition.
        for application_name, application in remote.definitions.items():
            if application_name not in self.definitions:
                application_tree = f"{tree}.definitions[{application_name!r}]"
                if self.delete_unmanaged:
                    logger.info("%s: (...) -> (deleted)", application_tree)
                    application._delete_remote(
                        secrets=secrets,
                        application_id=application_ids[application_name],
                    )
                    changed = True
                else:
                    logger.debug("%s: (...) (unmanaged)", application_tree)
        # Return whether or not the remote instance was changed.
        return changed
