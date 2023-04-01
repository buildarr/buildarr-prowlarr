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
Prowlarr plugin configuration.
"""


from __future__ import annotations

from typing import TYPE_CHECKING

from typing_extensions import Self

from ..types import ProwlarrConfigBase
from .ui import ProwlarrUISettings

# from .connect import SonarrConnectSettingsConfig
# from .download_clients import SonarrDownloadClientsSettingsConfig
# from .general import SonarrGeneralSettingsConfig
# from .indexers import ProwlarrIndexersSettings
# from .quality import SonarrQualitySettingsConfig
# from .tags import SonarrTagsSettingsConfig
# from .ui import SonarrUISettingsConfig

if TYPE_CHECKING:
    from ...secrets import ProwlarrSecrets


class ProwlarrSettings(ProwlarrConfigBase):
    """
    Prowlarr settings, used to configure a remote Prowlarr instance.
    """

    # indexers = ProwlarrIndexersSettings()
    # proxies = ProwlarrProxiesSettings()
    # download_clients = ProwlarrDownloadClientsSettings()
    # notifications = ProwlarrNotificationsSettings()
    # tags = ProwlarrTagsSettings()
    # general = SonarrGeneralSettingsConfig()
    ui = ProwlarrUISettings()

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
        # 2. Qualities must be updated before quality profiles.
        # 3. Indexers must be created before release profiles, and destroyed after they
        #    are no longer referenced by them.
        return any(
            [
                # self.tags.update_remote(
                #     f"{tree}.tags",
                #     secrets,
                #     remote.tags,
                #     check_unmanaged=check_unmanaged,
                # ),
                # self.quality.update_remote(
                #     f"{tree}.quality",
                #     secrets,
                #     remote.quality,
                #     check_unmanaged=check_unmanaged,
                # ),
                # self.indexers.update_remote(
                #     f"{tree}.indexers",
                #     secrets,
                #     remote.indexers,
                #     check_unmanaged=check_unmanaged,
                # ),
                # self.download_clients.update_remote(
                #     f"{tree}.download_clients",
                #     secrets,
                #     remote.download_clients,
                #     check_unmanaged=check_unmanaged,
                # ),
                # self.connect.update_remote(
                #     f"{tree}.connect",
                #     secrets,
                #     remote.connect,
                #     check_unmanaged=check_unmanaged,
                # ),
                # self.general.update_remote(
                #     f"{tree}.general",
                #     secrets,
                #     remote.general,
                #     check_unmanaged=check_unmanaged,
                # ),
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
