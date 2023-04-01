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
Prowlarr plugin type hints.
"""


from __future__ import annotations

from typing import Literal

from pydantic import ConstrainedStr, SecretStr

ProwlarrProtocol = Literal["http", "https"]


class LowerCaseStr(ConstrainedStr):
    to_lower = True


class ProwlarrApiKey(SecretStr):
    """
    Constrained secret string type for a Prowlarr API key.
    """

    min_length = 32
    max_length = 32
