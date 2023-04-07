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
Prowlarr plugin settings configuration.
"""


from __future__ import annotations

from typing import TYPE_CHECKING

from typing_extensions import Self

from ..types import ProwlarrConfigBase
from .apps import ProwlarrAppsSettings
from .download_clients import ProwlarrDownloadClientsSettings
from .general import ProwlarrGeneralSettings
from .indexers import ProwlarrIndexersSettings
from .notifications import ProwlarrNotificationsSettings
from .tags import ProwlarrTagsSettings
from .ui import ProwlarrUISettings

if TYPE_CHECKING:
    from ...secrets import ProwlarrSecrets


class ProwlarrSettings(ProwlarrConfigBase):
    """
    Prowlarr settings, used to configure a remote Prowlarr instance.
    """

    indexers: ProwlarrIndexersSettings = ProwlarrIndexersSettings()
    apps: ProwlarrAppsSettings = ProwlarrAppsSettings()
    download_clients: ProwlarrDownloadClientsSettings = ProwlarrDownloadClientsSettings()
    notifications: ProwlarrNotificationsSettings = ProwlarrNotificationsSettings()
    tags: ProwlarrTagsSettings = ProwlarrTagsSettings()
    general: ProwlarrGeneralSettings = ProwlarrGeneralSettings()
    ui: ProwlarrUISettings = ProwlarrUISettings()

    def update_remote(
        self,
        tree: str,
        secrets: ProwlarrSecrets,
        remote: Self,
        check_unmanaged: bool = False,
    ) -> bool:
        # Overload base function to guarantee execution order of section updates.
        # 1. Tags must be created before everything else, and destroyed after they
        #    are no longer referenced elsewhere.
        return any(
            [
                self.tags.update_remote(
                    f"{tree}.tags",
                    secrets,
                    remote.tags,
                    check_unmanaged=check_unmanaged,
                ),
                self.apps.update_remote(
                    f"{tree}.apps",
                    secrets,
                    remote.apps,
                    check_unmanaged=check_unmanaged,
                ),
                self.indexers.update_remote(
                    f"{tree}.indexers",
                    secrets,
                    remote.indexers,
                    check_unmanaged=check_unmanaged,
                ),
                self.download_clients.update_remote(
                    f"{tree}.download_clients",
                    secrets,
                    remote.download_clients,
                    check_unmanaged=check_unmanaged,
                ),
                self.notifications.update_remote(
                    f"{tree}.notifications",
                    secrets,
                    remote.notifications,
                    check_unmanaged=check_unmanaged,
                ),
                self.general.update_remote(
                    f"{tree}.general",
                    secrets,
                    remote.general,
                    check_unmanaged=check_unmanaged,
                ),
                self.ui.update_remote(
                    f"{tree}.ui",
                    secrets,
                    remote.ui,
                    check_unmanaged=check_unmanaged,
                ),
                # TODO: destroy indexers
                # TODO: destroy tags
            ],
        )
