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
Prowlarr plugin app sync profile configuration.
"""


from __future__ import annotations

from logging import getLogger
from typing import Any, Dict, List, Mapping

import prowlarr

from buildarr.config import RemoteMapEntry
from pydantic import PositiveInt
from typing_extensions import Self

from ....api import prowlarr_api_client
from ....secrets import ProwlarrSecrets
from ...types import ProwlarrConfigBase

logger = getLogger(__name__)


class SyncProfile(ProwlarrConfigBase):
    """
    The following configuration attributes are available for an app sync profile.
    """

    enable_rss: bool = True
    """
    Enable RSS searches/queries for the connected applications.
    """

    enable_interactive_search: bool = True
    """
    Enable interactive (manual) searches for the connection applications.
    """

    enable_automatic_search: bool = True
    """
    Enable automatic searches for the connected applications.
    """

    minimum_seeders: PositiveInt = 1
    """
    The minimum number of seeders required by the application to download a release.
    """

    _remote_map: List[RemoteMapEntry] = [
        ("enable_rss", "enableRss", {}),
        ("enable_interactive_search", "enableInteractiveSearch", {}),
        ("enable_automatic_search", "enableAutomaticSearch", {}),
        ("minimum_seeders", "minimumSeeders", {}),
    ]

    @classmethod
    def _from_remote(cls, remote_attrs: Mapping[str, Any]) -> Self:
        return cls(
            **cls.get_local_attrs(
                remote_map=cls._remote_map,
                remote_attrs=remote_attrs,
            ),
        )

    def _create_remote(self, tree: str, secrets: ProwlarrSecrets, profile_name: str) -> None:
        remote_attrs = {
            "name": profile_name,
            **self.get_create_remote_attrs(tree=tree, remote_map=self._remote_map),
        }
        with prowlarr_api_client(secrets=secrets) as api_client:
            prowlarr.AppProfileApi(api_client).create_app_profile(
                app_profile_resource=prowlarr.AppProfileResource.from_dict(remote_attrs),
            )

    def _update_remote(
        self,
        tree: str,
        secrets: ProwlarrSecrets,
        remote: Self,
        api_profile: prowlarr.AppProfileResource,
    ) -> bool:
        changed, updated_attrs = self.get_update_remote_attrs(
            tree=tree,
            remote=remote,
            remote_map=self._remote_map,
        )
        if changed:
            remote_attrs = {**api_profile.to_dict(), **updated_attrs}
            with prowlarr_api_client(secrets=secrets) as api_client:
                prowlarr.AppProfileApi(api_client).update_app_profile(
                    id=str(api_profile.id),
                    app_profile_resource=prowlarr.AppProfileResource.from_dict(remote_attrs),
                )
            return True
        return False

    def _delete_remote(self, tree: str, secrets: ProwlarrSecrets, profile_id: int) -> None:
        logger.info("%s: (...) -> (deleted)", tree)
        with prowlarr_api_client(secrets=secrets) as api_client:
            prowlarr.AppProfileApi(api_client).delete_app_profile(id=profile_id)


class SyncProfilesSettings(ProwlarrConfigBase):
    """
    App sync profiles are used to set application syncing configuration
    with respect to an indexer.

    Configure the sync profile in Buildarr:

    ```yaml
    prowlarr:
      settings:
        apps:
          sync_profiles:
            delete_unmanaged: false
            definitions:
              "Standard":
                enable_automatic_search: true
                enable_interactive_search: true
                enable_rss: true
                minimum_seeders: 1
    ```

    When the [`sync_profile`](
    ../indexers/indexers.md#buildarr_prowlarr.config.settings
    .indexers.indexers.Indexer.sync_profile
    )
    attribute on the indexer is set to the name of the
    sync profile, the applications connected to the indexer will respect
    the settings defined in the sync profile for that indexer.

    For more information, refer to the guide for
    [sync profiles](https://wiki.servarr.com/prowlarr/settings#sync-profiles)
    on WikiArr.
    """

    delete_unmanaged: bool = False
    """
    Automatically delete indexer proxies not configured in Buildarr.

    If unsure, leave set to the default value of `false`.
    """

    definitions: Dict[str, SyncProfile] = {}
    """
    Application sync profiles are defined here.
    """

    @classmethod
    def from_remote(cls, secrets: ProwlarrSecrets) -> Self:
        with prowlarr_api_client(secrets=secrets) as api_client:
            api_profiles = prowlarr.AppProfileApi(api_client).list_app_profile()
        return cls(
            definitions={
                api_profile.name: SyncProfile._from_remote(remote_attrs=api_profile.to_dict())
                for api_profile in api_profiles
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
            api_profiles = prowlarr.AppProfileApi(api_client).list_app_profile()
        # Compare local definitions to their remote equivalent.
        # If a local definition does not exist on the remote, create it.
        # If it does exist on the remote, attempt an an in-place modification,
        # and set the `changed` flag if modifications were made.
        for profile_name, profile in self.definitions.items():
            profile_tree = f"{tree}.definitions[{repr(profile_name)}]"
            if profile_name not in remote.definitions:
                profile._create_remote(
                    tree=profile_tree,
                    secrets=secrets,
                    profile_name=profile_name,
                )
                changed = True
            elif profile._update_remote(
                tree=profile_tree,
                secrets=secrets,
                remote=remote.definitions[profile_name],  # type: ignore[arg-type]
                api_profile=api_profiles[profile_name],
            ):
                changed = True
        # Traverse the remote definitions, and see if there are any remote definitions
        # that do not exist in the local configuration.
        # If `delete_unmanaged` is enabled, delete it from the remote.
        # If `delete_unmanaged` is disabled, just add a log entry acknowledging
        # the existence of the unmanaged definition.
        for profile_name, profile in remote.definitions.items():
            if profile_name not in self.definitions:
                profile_tree = f"{tree}.definitions[{repr(profile_name)}]"
                if self.delete_unmanaged:
                    profile._delete_remote(
                        tree=profile_tree,
                        secrets=secrets,
                        profile_id=api_profiles[profile_name].id,
                    )
                    changed = True
                else:
                    logger.debug("%s: (...) (unmanaged)", profile_tree)
        # Return whether or not the remote instance was changed.
        return changed
