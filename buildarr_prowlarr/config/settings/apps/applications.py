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

import itertools

from logging import getLogger
from typing import Any, Dict, List, Literal, Mapping, Optional, Set, Tuple, Type, Union

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
    """ """

    disabled = "disabled"
    add_and_remove_only = "addOnly"
    full_sync = "fullSync"


class Application(ProwlarrConfigBase):
    """
    Base class for a Prowlarr notification connection.
    """

    type: str
    """
    Type value associated with this kind of connection.
    """

    prowlarr_url: AnyHttpUrl
    """
    Prowlarr server URL as the target application sees it, including http(s)://, port,
    and URL base (if needed).
    """

    base_url: AnyHttpUrl
    """
    URL used to connect to the target application server, including http(s)://, port,
    and URL base (if needed).
    """

    # Define per-type because the API key spec may differ between them,
    # and if an application link is present, it is not required.
    # api_key: ArrApiKey

    sync_level: SyncLevel = SyncLevel.add_and_remove_only

    # Define per-type defaults.
    sync_categories: Set[LowerCaseNonEmptyStr]
    """
    Categories of content to sync with the target application.

    Each type of application has individually set default values.

    Note that only categories supported by the application will actually be used.
    """

    tags: Set[NonEmptyStr] = set()
    """
    Prowlarr tags to associate this application link with.
    """

    _remote_map: List[RemoteMapEntry] = []

    @classmethod
    def _get_base_remote_map(
        cls,
        category_ids: Mapping[str, int],
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
                    "decoder": lambda v: set(
                        (
                            category
                            for category, category_id in category_ids.items()
                            if category_id in v
                        ),
                    ),
                    "encoder": lambda v: sorted(category_ids[category] for category in v),
                    "is_field": True,
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
    def _from_remote(
        cls,
        category_ids: Mapping[str, int],
        tag_ids: Mapping[str, int],
        remote_attrs: Mapping[str, Any],
    ) -> Self:
        return cls(
            **cls.get_local_attrs(
                remote_map=cls._get_base_remote_map(category_ids, tag_ids) + cls._remote_map,
                remote_attrs=remote_attrs,
            ),
        )

    def _get_schema(self, schemas: List[prowlarr.IndexerResource]) -> Dict[str, Any]:
        return {
            k: v
            for k, v in next(
                s for s in schemas if s.implementation_name.lower() == self.type.lower()
            )
            .to_dict()
            .items()
            if k not in ["id", "name"]
        }

    def _create_remote(
        self,
        tree: str,
        secrets: ProwlarrSecrets,
        application_schemas: List[prowlarr.ApplicationResource],
        category_ids: Mapping[str, int],
        tag_ids: Mapping[str, int],
        application_name: str,
    ) -> None:
        schema = self._get_schema(application_schemas)
        set_attrs = self.get_create_remote_attrs(
            tree=tree,
            remote_map=self._get_base_remote_map(category_ids, tag_ids) + self._remote_map,
        )
        field_values: Dict[str, Any] = {
            field["name"]: field["value"] for field in set_attrs["fields"]
        }
        set_attrs["fields"] = [
            ({**f, "value": field_values[f["name"]]} if f["name"] in field_values else f)
            for f in schema["fields"]
        ]
        remote_attrs = {"name": application_name, **schema, **set_attrs}
        with prowlarr_api_client(secrets=secrets) as api_client:
            prowlarr.ApplicationApi(api_client).create_applications(
                notification_resource=prowlarr.ApplicationResource.from_dict(remote_attrs),
            )

    def _update_remote(
        self,
        tree: str,
        secrets: ProwlarrSecrets,
        remote: Self,
        application_schemas: List[prowlarr.ApplicationResource],
        category_ids: Mapping[str, int],
        tag_ids: Mapping[str, int],
        api_application: prowlarr.ApplicationResource,
    ) -> bool:
        schema = self._get_schema(application_schemas)
        changed, updated_attrs = self.get_update_remote_attrs(
            tree=tree,
            remote=remote,
            remote_map=self._get_base_remote_map(category_ids, tag_ids) + self._remote_map,
        )
        if changed:
            with prowlarr_api_client(secrets=secrets) as api_client:
                application_api = prowlarr.ApplicationApi(api_client)
                if "fields" in updated_attrs:
                    field_values: Dict[str, Any] = {
                        field["name"]: field["value"] for field in updated_attrs["fields"]
                    }
                    updated_attrs["fields"] = [
                        (
                            {**f, "value": field_values[f["name"]]}
                            if f["name"] in field_values
                            else f
                        )
                        for f in schema["fields"]
                    ]
                remote_attrs = {**api_application.to_dict(), **updated_attrs}
                application_api.update_applications(
                    id=str(api_application.id),
                    notification_resource=prowlarr.ApplicationResource.from_dict(remote_attrs),
                )
            return True
        return False

    def _delete_remote(self, tree: str, secrets: ProwlarrSecrets, application_id: int) -> None:
        logger.info("%s: (...) -> (deleted)", tree)
        with prowlarr_api_client(secrets=secrets) as api_client:
            prowlarr.ApplicationApi(api_client).delete_applications(id=application_id)


class LazylibraryApplication(Application):
    """
    Receive media update and health alert push notifications via Boxcar.

    Supported notification triggers: All except `on_rename`
    """

    type: Literal["lazylibrary"] = "lazylibrary"
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

    _remote_map: List[RemoteMapEntry] = [("api_key", "apiKey", {"is_field": True})]


class LidarrApplication(Application):
    """
    Receive media update and health alert push notifications via Boxcar.

    Supported notification triggers: All except `on_rename`
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

    _remote_map: List[RemoteMapEntry] = [("api_key", "apiKey", {"is_field": True})]


class MylarApplication(Application):
    """
    Receive media update and health alert push notifications via Boxcar.

    Supported notification triggers: All except `on_rename`
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

    _remote_map: List[RemoteMapEntry] = [("api_key", "apiKey", {"is_field": True})]


class RadarrApplication(Application):
    """
    Receive media update and health alert push notifications via Boxcar.

    Supported notification triggers: All except `on_rename`
    """

    type: Literal["radarr"] = "radarr"
    """
    Type value associated with this kind of application.
    """

    api_key: ArrApiKey
    """
    API key used to access the target instance.
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

    _remote_map: List[RemoteMapEntry] = [("api_key", "apiKey", {"is_field": True})]


class ReadarrApplication(Application):
    """
    Receive media update and health alert push notifications via Boxcar.

    Supported notification triggers: All except `on_rename`
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

    _remote_map: List[RemoteMapEntry] = [("api_key", "apiKey", {"is_field": True})]


class SonarrApplication(Application):
    """
    Receive media update and health alert push notifications via Boxcar.

    Supported notification triggers: All except `on_rename`
    """

    type: Literal["sonarr"] = "sonarr"
    """
    Type value associated with this kind of application
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

    @validator("api_key")
    def validate_api_key(cls, value: Optional[SecretStr], values: Dict[str, Any]) -> SecretStr:
        if "instance_name" in values and values["instance_name"]:
            return state.secrets.sonarr[  # type: ignore[attr-defined]
                values["instance_name"]
            ].api_key
        elif not value:
            raise ValueError("required when 'instance_name' is not defined")
        return value

    @classmethod
    def _get_base_remote_map(
        cls,
        category_ids: Mapping[str, int],
        tag_ids: Mapping[str, int],
    ) -> List[RemoteMapEntry]:
        return [
            *super()._get_base_remote_map(category_ids, tag_ids),
            ("api_key", "apiKey", {"is_field": True}),
            (
                "anime_sync_categories",
                "animeSyncCategories",
                {
                    "decoder": lambda v: set(
                        (
                            category
                            for category, category_id in category_ids.items()
                            if category_id in v
                        ),
                    ),
                    "encoder": lambda v: sorted(category_ids[category] for category in v),
                    "is_field": True,
                },
            ),
        ]


class WhisparrApplication(Application):
    """
    Receive media update and health alert push notifications via Boxcar.

    Supported notification triggers: All except `on_rename`
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

    _remote_map: List[RemoteMapEntry] = [("api_key", "apiKey", {"is_field": True})]


APPLICATION_TYPE_MAP: Dict[str, Type[Application]] = {
    "lazylibrary": LazylibraryApplication,
    "lidarr": LidarrApplication,
    "mylar": MylarApplication,
    "radarr": RadarrApplication,
    "readarr": ReadarrApplication,
    "sonarr": SonarrApplication,
    "whisparr": WhisparrApplication,
}

APPLICATION_TYPES: Tuple[Type[Application], ...] = tuple(APPLICATION_TYPE_MAP.values())

ApplicationType = Union[
    LazylibraryApplication,
    LidarrApplication,
    MylarApplication,
    RadarrApplication,
    ReadarrApplication,
    SonarrApplication,
    WhisparrApplication,
]


class ApplicationsSettings(ProwlarrConfigBase):
    """
    Manage application links in Prowlarr.
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
            category_ids: Dict[str, int] = {
                api_category.name: api_category.id
                for api_category in itertools.chain.from_iterable(
                    api_category_group.sub_categories
                    for api_category_group in prowlarr.IndexerDefaultCategoriesApi(
                        api_client,
                    ).list_indexer_categories()
                )
            }
            api_applications = prowlarr.ApplicationApi(api_client).list_applications()
            tag_ids: Dict[str, int] = (
                {tag.label: tag.id for tag in prowlarr.TagApi(api_client).list_tag()}
                if any(api_application.tags for api_application in api_applications)
                else {}
            )
        return cls(
            definitions={
                api_application.name: APPLICATION_TYPE_MAP[
                    api_application.implementation_name.lower()
                ]._from_remote(
                    category_ids=category_ids,
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
        #
        changed = False
        #
        with prowlarr_api_client(secrets=secrets) as api_client:
            application_api = prowlarr.ApplicationApi(api_client)
            application_schemas = application_api.list_applications_schema()
            api_applications = {
                api_application.name: api_application
                for api_application in application_api.list_applications()
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
                if any(application.tags for application in self.definitions.values())
                or any(application.tags for application in remote.definitions.values())
                else {}
            )
        #
        for application_name, application in self.definitions.items():
            application_tree = f"{tree}.definitions[{repr(application_name)}]"
            #
            if application_name not in remote.definitions:
                application._create_remote(
                    tree=application_tree,
                    secrets=secrets,
                    application_schemas=application_schemas,
                    category_ids=category_ids,
                    tag_ids=tag_ids,
                    application_name=application_name,
                )
                changed = True
            #
            elif application._update_remote(
                tree=application_tree,
                secrets=secrets,
                remote=remote.definitions[application_name],  # type: ignore[arg-type]
                application_schemas=application_schemas,
                category_ids=category_ids,
                tag_ids=tag_ids,
                api_application=api_applications[application_name],
            ):
                changed = True
        #
        for application_name, application in remote.definitions.items():
            if application_name not in self.definitions:
                application_tree = f"{tree}.definitions[{repr(application_name)}]"
                if self.delete_unmanaged:
                    application._delete_remote(
                        tree=application_tree,
                        secrets=secrets,
                        application_id=api_applications[application_name].id,
                    )
                    changed = True
                else:
                    logger.debug("%s: (...) (unmanaged)", application_tree)
        #
        return changed
