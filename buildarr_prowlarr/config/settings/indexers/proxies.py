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
Prowlarr plugin indexer proxy settings configuration.
"""


from __future__ import annotations

from logging import getLogger
from typing import Any, Dict, List, Literal, Mapping, Optional, Set, Tuple, Type, Union

import prowlarr

from buildarr.config import RemoteMapEntry
from buildarr.types import BaseEnum, NonEmptyStr, Port
from pydantic import AnyHttpUrl, Field, PositiveFloat, SecretStr
from typing_extensions import Annotated, Self

from ....api import prowlarr_api_client
from ....secrets import ProwlarrSecrets
from ...types import ProwlarrConfigBase

logger = getLogger(__name__)


class SyncLevel(BaseEnum):
    """ """

    disabled = "disabled"
    add_and_remove_only = "addOnly"
    full_sync = "fullSync"


class Proxy(ProwlarrConfigBase):
    """
    Base class for a Prowlarr indexer proxy.
    """

    type: str
    """
    Type value associated with this kind of proxy.
    """

    tags: Set[NonEmptyStr] = set()
    """
    Prowlarr tags to associate this indexer proxy with.
    """

    _remote_map: List[RemoteMapEntry]

    @classmethod
    def _get_base_remote_map(cls, tag_ids: Mapping[str, int]) -> List[RemoteMapEntry]:
        return [
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
    def _from_remote(cls, tag_ids: Mapping[str, int], remote_attrs: Mapping[str, Any]) -> Self:
        return cls(
            **cls.get_local_attrs(
                remote_map=cls._get_base_remote_map(tag_ids) + cls._remote_map,
                remote_attrs=remote_attrs,
            ),
        )

    def _get_api_schema(self, schemas: List[prowlarr.IndexerProxyResource]) -> Dict[str, Any]:
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
        api_proxy_schemas: List[prowlarr.IndexerProxyResource],
        tag_ids: Mapping[str, int],
        proxy_name: str,
    ) -> None:
        api_schema = self._get_api_schema(api_proxy_schemas)
        set_attrs = self.get_create_remote_attrs(
            tree=tree,
            remote_map=self._get_base_remote_map(tag_ids) + self._remote_map,
        )
        field_values: Dict[str, Any] = {
            field["name"]: field["value"] for field in set_attrs["fields"]
        }
        set_attrs["fields"] = [
            ({**f, "value": field_values[f["name"]]} if f["name"] in field_values else f)
            for f in api_schema["fields"]
        ]
        remote_attrs = {"name": proxy_name, **api_schema, **set_attrs}
        with prowlarr_api_client(secrets=secrets) as api_client:
            prowlarr.IndexerProxyApi(api_client).create_indexer_proxy(
                notification_resource=prowlarr.IndexerProxyResource.from_dict(remote_attrs),
            )

    def _update_remote(
        self,
        tree: str,
        secrets: ProwlarrSecrets,
        remote: Self,
        api_proxy_schemas: List[prowlarr.IndexerProxyResource],
        tag_ids: Mapping[str, int],
        api_proxy: prowlarr.IndexerProxyResource,
    ) -> bool:
        api_schema = self._get_api_schema(api_proxy_schemas)
        changed, updated_attrs = self.get_update_remote_attrs(
            tree=tree,
            remote=remote,
            remote_map=self._get_base_remote_map(tag_ids) + self._remote_map,
        )
        if changed:
            if "fields" in updated_attrs:
                field_values: Dict[str, Any] = {
                    field["name"]: field["value"] for field in updated_attrs["fields"]
                }
                updated_attrs["fields"] = [
                    ({**f, "value": field_values[f["name"]]} if f["name"] in field_values else f)
                    for f in api_schema["fields"]
                ]
            remote_attrs = {**api_proxy.to_dict(), **updated_attrs}
            with prowlarr_api_client(secrets=secrets) as api_client:
                prowlarr.IndexerProxyApi(api_client).update_indexer_proxy(
                    id=str(api_proxy.id),
                    indexer_proxy_resource=prowlarr.IndexerProxyResource.from_dict(remote_attrs),
                )
            return True
        return False

    def _delete_remote(self, tree: str, secrets: ProwlarrSecrets, proxy_id: int) -> None:
        logger.info("%s: (...) -> (deleted)", tree)
        with prowlarr_api_client(secrets=secrets) as api_client:
            prowlarr.IndexerProxyApi(api_client).delete_indexer_proxy(id=proxy_id)


class FlaresolverrProxy(Proxy):
    """
    Receive media update and health alert push notifications via Boxcar.

    Supported notification triggers: All except `on_rename`
    """

    type: Literal["flaresolverr"] = "flaresolverr"
    """
    Type value associated with this kind of proxy.
    """

    host_url: AnyHttpUrl
    """
    Host URL to connect to the Flaresolverr instance, from the Prowlarr instance's persective.
    """

    request_timeout: PositiveFloat = 60  # seconds
    """
    Timeout for requests sent to FlareSolverr, in seconds.
    """

    _remote_map: List[RemoteMapEntry] = [
        ("host_url", "host", {"is_field": True}),
        ("request_timeout", "requestTimeout", {"is_field": True}),
    ]


class HttpProxy(Proxy):
    """
    Receive media update and health alert push notifications via Boxcar.

    Supported notification triggers: All except `on_rename`
    """

    type: Literal["http"] = "http"
    """
    Type value associated with this kind of proxy.
    """

    hostname: NonEmptyStr
    """
    Hostname of the proxy server.
    """

    port: Port = 8080  # type: ignore[assignment]
    """
    Access port for the proxy.
    """

    username: Optional[str] = None
    """
    Username used to authenticate with the proxy, if required.
    """

    password: Optional[SecretStr] = None
    """
    Password used to authenticate with the proxy, if required.
    """

    _remote_map: List[RemoteMapEntry] = [
        ("hostname", "host", {"is_field": True}),
        ("port", "port", {"is_field": True}),
        (
            "username",
            "username",
            {
                "decoder": lambda v: v or None,
                "encoder": lambda v: v or "",
                "is_field": True,
            },
        ),
        (
            "password",
            "password",
            {
                "decoder": lambda v: SecretStr(v) if v else None,
                "encoder": lambda v: v.get_secret_value() if v else "",
                "is_field": True,
            },
        ),
    ]


class Socks4Proxy(Proxy):
    """
    Receive media update and health alert push notifications via Boxcar.

    !!! note

        SOCKS4 does not support full username-based authentication,
        even though Prowlarr exposes the configuration attribbutes.

        If you would like to secure your proxy server, upgrade to SOCKS5
        or switch to using an HTTP proxy.
    """

    type: Literal["socks4"] = "socks4"
    """
    Type value associated with this kind of proxy.
    """

    hostname: NonEmptyStr
    """
    Hostname of the proxy server.
    """

    port: Port = 1080  # type: ignore[assignment]
    """
    Access port for the proxy.
    """

    username: Optional[str] = None
    """
    Username used to authenticate with the proxy, if required.
    """

    password: Optional[SecretStr] = None
    """
    Password used to authenticate with the proxy, if required.
    """

    _remote_map: List[RemoteMapEntry] = [
        ("hostname", "host", {"is_field": True}),
        ("port", "port", {"is_field": True}),
        (
            "username",
            "username",
            {
                "decoder": lambda v: v or None,
                "encoder": lambda v: v or "",
                "is_field": True,
            },
        ),
        (
            "password",
            "password",
            {
                "decoder": lambda v: SecretStr(v) if v else None,
                "encoder": lambda v: v.get_secret_value() if v else "",
                "is_field": True,
            },
        ),
    ]


class Socks5Proxy(Proxy):
    """
    Receive media update and health alert push notifications via Boxcar.

    Supported notification triggers: All except `on_rename`
    """

    type: Literal["socks5"] = "socks5"
    """
    Type value associated with this kind of proxy.
    """

    hostname: NonEmptyStr
    """
    Hostname of the proxy server.
    """

    port: Port = 1080  # type: ignore[assignment]
    """
    Access port for the proxy.
    """

    username: Optional[str] = None
    """
    Username used to authenticate with the proxy, if required.
    """

    password: Optional[SecretStr] = None
    """
    Password used to authenticate with the proxy, if required.
    """

    _remote_map: List[RemoteMapEntry] = [
        ("hostname", "host", {"is_field": True}),
        ("port", "port", {"is_field": True}),
        (
            "username",
            "username",
            {
                "decoder": lambda v: v or None,
                "encoder": lambda v: v or "",
                "is_field": True,
            },
        ),
        (
            "password",
            "password",
            {
                "decoder": lambda v: SecretStr(v) if v else None,
                "encoder": lambda v: v.get_secret_value() if v else "",
                "is_field": True,
            },
        ),
    ]


PROXY_TYPE_MAP: Dict[str, Type[Proxy]] = {
    "flaresolverr": FlaresolverrProxy,
    "http": HttpProxy,
    "socks4": Socks4Proxy,
    "socks5": Socks5Proxy,
}

PROXY_TYPES: Tuple[Type[Proxy], ...] = tuple(PROXY_TYPE_MAP.values())

ProxyType = Union[
    FlaresolverrProxy,
    HttpProxy,
    Socks4Proxy,
    Socks5Proxy,
]


class ProxiesSettings(ProwlarrConfigBase):
    """
    Manage indexer proxies in Prowlarr.
    """

    delete_unmanaged: bool = False
    """
    Automatically delete indexer proxies not configured in Buildarr.

    Take care when enabling this option, as this can remove connections automatically
    managed by other applications.
    """

    definitions: Dict[str, Annotated[ProxyType, Field(discriminator="type")]] = {}
    """
    Indexer proxy definitions to configure in Prowlarr.
    """

    @classmethod
    def from_remote(cls, secrets: ProwlarrSecrets) -> Self:
        with prowlarr_api_client(secrets=secrets) as api_client:
            api_proxies = prowlarr.IndexerProxyApi(api_client).list_indexer_proxy()
            tag_ids: Dict[str, int] = (
                {tag.label: tag.id for tag in prowlarr.TagApi(api_client).list_tag()}
                if any(api_proxy.tags for api_proxy in api_proxies)
                else {}
            )
        return cls(
            definitions={
                api_proxy["name"]: PROXY_TYPE_MAP[
                    api_proxy["implementationName"].lower()
                ]._from_remote(tag_ids=tag_ids, remote_attrs=api_proxy.to_dict())
                for api_proxy in api_proxies
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
            indexer_proxy_api = prowlarr.IndexerProxyApi(api_client)
            api_proxy_schemas = indexer_proxy_api.list_indexer_proxy_schema()
            api_proxies = {
                api_proxy.name: api_proxy for api_proxy in indexer_proxy_api.list_indexer_proxy()
            }
            tag_ids: Dict[str, int] = (
                {tag.label: tag.id for tag in prowlarr.TagApi(api_client).list_tag()}
                if any(proxy.tags for proxy in self.definitions.values())
                or any(proxy.tags for proxy in remote.definitions.values())
                else {}
            )
        #
        for proxy_name, proxy in self.definitions.items():
            proxy_tree = f"{tree}.definitions[{repr(proxy_name)}]"
            #
            if proxy_name not in remote.definitions:
                proxy._create_remote(
                    tree=proxy_tree,
                    secrets=secrets,
                    api_proxy_schemas=api_proxy_schemas,
                    tag_ids=tag_ids,
                    proxy_name=proxy_name,
                )
                changed = True
            #
            elif proxy._update_remote(
                tree=proxy_tree,
                secrets=secrets,
                remote=remote.definitions[proxy_name],  # type: ignore[arg-type]
                api_proxy_schemas=api_proxy_schemas,
                tag_ids=tag_ids,
                api_proxy=api_proxies[proxy_name],
            ):
                changed = True
        #
        for proxy_name, proxy in remote.definitions.items():
            if proxy_name not in self.definitions:
                proxy_tree = f"{tree}.definitions[{repr(proxy_name)}]"
                if self.delete_unmanaged:
                    proxy._delete_remote(
                        tree=proxy_tree,
                        secrets=secrets,
                        proxy_id=api_proxies[proxy_name].id,
                    )
                    changed = True
                else:
                    logger.debug("%s: (...) (unmanaged)", proxy_tree)
        #
        return changed
