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
Prowlarr plugin tags configuration.
"""


from __future__ import annotations

from logging import getLogger
from typing import Dict, Set

import prowlarr

from buildarr.types import NonEmptyStr
from typing_extensions import Self

from ...api import prowlarr_api_client
from ...secrets import ProwlarrSecrets
from ..types import ProwlarrConfigBase

logger = getLogger(__name__)


class ProwlarrTagsSettings(ProwlarrConfigBase):
    """
    Tags are used to associate media files with certain resources (e.g. indexers).

    ```yaml
    prowlarr:
      settings:
        tags:
          definitions:
            - "example1"
            - "example2"
    ```

    To be able to use those tags in Buildarr, they need to be defined
    in this configuration section.
    """

    definitions: Set[NonEmptyStr] = set()
    """
    Define tags that are used within Buildarr here.

    If they are not defined here, you may get errors resulting from non-existent
    tags from either Buildarr or Prowlarr.
    """

    @classmethod
    def from_remote(cls, secrets: ProwlarrSecrets) -> Self:
        with prowlarr_api_client(secrets=secrets) as api_client:
            tags = prowlarr.TagApi(api_client).list_tag()
        return cls(definitions=[tag.label for tag in tags])

    def update_remote(
        self,
        tree: str,
        secrets: ProwlarrSecrets,
        remote: Self,
        check_unmanaged: bool = False,
    ) -> bool:
        # This only does creations and updates, as Prowlarr automatically cleans up unused tags.
        changed = False
        with prowlarr_api_client(secrets=secrets) as api_client:
            tag_api = prowlarr.TagApi(api_client)
            current_tags: Dict[str, int] = {tag.label: tag.id for tag in tag_api.list_tag()}
            if self.definitions:
                for i, tag in enumerate(self.definitions):
                    if tag in current_tags:
                        logger.debug("%s.definitions[%i]: %s (exists)", tree, i, repr(tag))
                    else:
                        logger.info("%s.definitions[%i]: %s -> (created)", tree, i, repr(tag))
                        tag_api.create_tag(prowlarr.TagResource.from_dict({"label": tag}))
                        changed = True
        return changed
