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
Prowlarr plugin indexer configuration section.
"""


from __future__ import annotations

from typing import TYPE_CHECKING

from typing_extensions import Self

from ...types import ProwlarrConfigBase
from .indexers import IndexersSettings
from .proxies import ProxiesSettings

if TYPE_CHECKING:
    from ....secrets import ProwlarrSecrets


class ProwlarrIndexersSettings(ProwlarrConfigBase):
    indexers: IndexersSettings = IndexersSettings()
    proxies: ProxiesSettings = ProxiesSettings()

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
                self.proxies.update_remote(
                    f"{tree}.proxies",
                    secrets,
                    remote.proxies,
                    check_unmanaged=check_unmanaged,
                ),
                self.indexers.update_remote(
                    f"{tree}.indexers",
                    secrets,
                    remote.indexers,
                    check_unmanaged=check_unmanaged,
                ),
                # TODO: destroy indexers
                # TODO: destroy tags
            ],
        )
