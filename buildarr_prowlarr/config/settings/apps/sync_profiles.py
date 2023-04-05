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
Prowlarr plugin application sync profile configuration.
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
    Base class for an application sync profile.
    """

    enable_rss: bool = True
    """
    Enable the RSS feed for applicable indexers.
    """

    enable_interactive_search: bool = True
    """
    Enable interactive search for applicable indexers.

    The indexers will be used when interactive searches are performed in the UI.
    """

    enable_automatic_search: bool = True
    """
    Enable automatic searches for applicable indexers.

    The indexers will be used when automatic searches are perfomed
    in the UI, or by Prowlarr itse.f
    """

    minimum_seeders: PositiveInt = 1
    """
    The minimum number of seeders required by the application
    for the indexer to download a release.
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
    Manage indexer proxies in Prowlarr.
    """

    delete_unmanaged: bool = False
    """
    Automatically delete indexer proxies not configured in Buildarr.

    Take care when enabling this option, as this can remove connections automatically
    managed by other applications.
    """

    definitions: Dict[str, SyncProfile] = {}
    """
    Application sync profile definitions to configure in Prowlarr.
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
        changed = False
        with prowlarr_api_client(secrets=secrets) as api_client:
            api_profiles = prowlarr.AppProfileApi(api_client).list_app_profile()
        #
        for profile_name, profile in self.definitions.items():
            profile_tree = f"{tree}.definitions[{repr(profile_name)}]"
            if profile_name not in remote.definitions:
                profile._create_remote(
                    tree=profile_tree,
                    secrets=secrets,
                    profile_name=profile_name,
                )
                changed = True
            #
            elif profile._update_remote(
                tree=profile_tree,
                secrets=secrets,
                remote=remote.definitions[profile_name],  # type: ignore[arg-type]
                api_profile=api_profiles[profile_name],
            ):
                changed = True
        #
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
        #
        return changed
