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
Prowlarr plugin general settings configuration.
"""


from __future__ import annotations

from ipaddress import IPv4Address
from typing import Any, Dict, List, Literal, Mapping, Optional, Set, Tuple, Union

import prowlarr

from buildarr.config import RemoteMapEntry
from buildarr.types import BaseEnum, NonEmptyStr, Password, Port
from pydantic import Field, SecretStr, validator
from typing_extensions import Self

from ...api import prowlarr_api_client
from ...secrets import ProwlarrSecrets
from ..types import ProwlarrConfigBase


class AuthenticationMethod(BaseEnum):
    """
    Prowlarr authentication method.
    """

    none = "none"
    basic = "basic"
    form = "forms"


class AuthenticationRequired(BaseEnum):
    """
    Authentication requirement settings.
    """

    enabled = "enabled"
    local_disabled = "disabledForLocalAddresses"


class CertificateValidation(BaseEnum):
    """
    External site HTTPS certification validation method.
    """

    enabled = "enabled"
    local_disabled = "disabledForLocalAddresses"
    disabled = "disabled"


class ProxyType(BaseEnum):
    """
    Proxy server type.
    """

    http = "http"
    socks4 = "socks4"
    socks5 = "socks5"


class ProwlarrLogLevel(BaseEnum):
    """
    Log level of the Prowlarr application.
    """

    INFO = "info"
    DEBUG = "debug"
    TRACE = "trace"


class UpdateMechanism(BaseEnum):
    """
    Prowlarr updating mechanism.
    """

    builtin = "builtIn"
    script = "script"
    external = "external"
    apt = "apt"
    docker = "docker"


class GeneralSettings(ProwlarrConfigBase):
    """
    Prowlarr general settings base class.
    """

    _remote_map: List[RemoteMapEntry]

    @classmethod
    def _from_remote(cls, remote_attrs: Mapping[str, Any]) -> Self:
        return cls(**cls.get_local_attrs(cls._remote_map, remote_attrs))

    def _update_remote_attrs(
        self,
        tree: str,
        secrets: ProwlarrSecrets,
        remote: Self,
        check_unmanaged: bool = False,
    ) -> Tuple[bool, Dict[str, Any]]:
        return self.get_update_remote_attrs(
            tree,
            remote,
            self._remote_map,
            check_unmanaged=check_unmanaged,
            set_unchanged=True,
        )


class HostGeneralSettings(GeneralSettings):
    """
    Prowlarr instance connection and name configuration.

    Many of these settings configure Prowlarr's external connection interface.
    If they are changed, the [settings Buildarr uses to connect](../host.md) with this
    Prowlarr instance may need to be updated, so take care when modifying them.

    **Changing any of these settings require a restart of Prowlarr to take effect.**
    """

    # According to docs, IPv6 not supported at this time.
    bind_address: Union[Literal["*"], IPv4Address] = "*"
    """
    Bind address for Prowlarr. Set to an IPv4 address bound to a local interface
    or `*` to bind on all interfaces.

    Unless you run Prowlarr directly on a host machine (i.e. not via Docker) and
    want Prowlarr to only be available on a specific network or interface,
    this generally should be left untouched.
    """

    port: Port = 9696  # type: ignore[assignment]
    """
    Unencrypted (HTTP) listening port for Prowlarr.

    If Prowlarr is being run via Docker in the default bridge mode,
    this setting shouldn't be changed.
    Instead, change the external port it is bound to using
    `--publish <port number>:9696`.
    """

    ssl_port: Port = 6969  # type: ignore[assignment]
    """
    Encrypted (HTTPS) listening port for Prowlarr.

    If Prowlarr is being run via Docker in the default bridge mode,
    this setting shouldn't be changed.
    Instead, change the external port it is bound to using
    `--publish <port number>:6969`.
    """

    use_ssl: bool = False
    """
    Enable the encrypted (HTTPS) listening port in Prowlarr.

    Instead of enabling HTTPS directly on Prowlarr, it is recommended
    to put Prowlarr behind a HTTPS-terminating reverse proxy such as Nginx, Caddy or Traefik.
    """

    ssl_cert_path: Optional[str] = None
    """
    Path to the TLS certificate file, in PFX format.

    Required if encryption (HTTPS) is enabled.
    """

    ssl_cert_password: Optional[SecretStr] = None
    """
    Password to unlock the TLS certificate file, if required.
    """

    url_base: Optional[str] = None
    """
    Add a prefix to all Prowlarr URLs,
    e.g. `http://localhost:9696/<url_base>/settings/general`.

    Generally used to accommodate reverse proxies where Prowlarr
    is assigned to a subfolder, e.g. `https://example.com/prowlarr`.
    """

    instance_name: NonEmptyStr = "Prowlarr"  # type: ignore[assignment]
    """
    Instance name in the browser tab and in syslog.
    """

    _remote_map: List[RemoteMapEntry] = [
        ("bind_address", "bindAddress", {}),
        ("port", "port", {}),
        ("ssl_port", "sslPort", {}),
        ("use_ssl", "enableSsl", {}),
        (
            "ssl_cert_path",
            "sslCertPath",
            {"decoder": lambda v: v or None, "encoder": lambda v: v or ""},
        ),
        (
            "ssl_cert_password",
            "sslCertPassword",
            {
                "decoder": lambda v: SecretStr(v) if v else None,
                "encoder": lambda v: v.get_secret_value() if v else "",
            },
        ),
        ("url_base", "urlBase", {"decoder": lambda v: v or None, "encoder": lambda v: v or ""}),
        ("instance_name", "instanceName", {}),
    ]


class SecurityGeneralSettings(GeneralSettings):
    """
    Prowlarr instance security (authentication) settings.
    """

    authentication: AuthenticationMethod = AuthenticationMethod.none
    """
    Authentication method for logging into Prowlarr.
    By default, do not require authentication.

    Values:

    * `none` - No authentication
    * `basic` - Authentication using HTTP basic auth (browser popup)
    * `form` - Authentication using a login page

    Requires a restart of Prowlarr to take effect.
    """

    authentication_required: AuthenticationRequired = AuthenticationRequired.enabled
    """
    Authentication requirement settings for accessing Prowlarr.

    Values:

    * `enabled` - Enabled
    * `local-disabled` - Disabled for Local Addresses
    """

    username: Optional[str] = None
    """
    Username for the administrator user. Required if authentication is enabled.

    Requires a restart of Prowlarr to take effect.
    """

    password: Optional[Password] = None
    """
    Password for the administrator user. Required if authentication is enabled.

    Requires a restart of Prowlarr to take effect.
    """

    certificate_validation: CertificateValidation = CertificateValidation.enabled
    """
    Change how strict HTTPS certification validation is.
    Do not change unless you understand the risks.

    Values:

    * `enabled` - Validate HTTPS certificates for all hosts
    * `local-disabled` - Disable HTTPS certificate validation for hosts on the local network
    * `disabled` - Disable HTTPS certificate validation completely
    """

    _remote_map: List[RemoteMapEntry] = [
        ("authentication", "authenticationMethod", {}),
        ("authentication_required", "authenticationRequired", {}),
        (
            "username",
            "username",
            {
                # Set to default value (`None`) if not found on remote.
                "optional": True,
                # Due to the validator, gets set to `None` if authentication is disabled
                # on the remote instance.
                "decoder": lambda v: v or None,
                # Prowlarr isn't too picky about this, but replicate the behaviour of the UI.
                "encoder": lambda v: v or "",
            },
        ),
        (
            "password",
            "password",
            {
                # Set to default value (`None`) if not found on remote.
                "optional": True,
                # Due to the validator, gets set to `None` if authentication is disabled
                # on the remote instance.
                "decoder": lambda v: v or None,
                # Prowlarr isn't too picky about this, but replicate the behaviour of the UI.
                "encoder": lambda v: v.get_secret_value() if v else "",
            },
        ),
        ("certificate_validation", "certificateValidation", {}),
    ]

    @validator("username", "password")
    def required_when_auth_enabled(
        cls,
        value: Optional[str],
        values: Dict[str, Any],
    ) -> Optional[str]:
        """
        Enforce the following constraints on the validated attributes:

        * If `authentication` is `none`, set the attribute value to `None`.
        * If `authentication` is a value other than `none` (i.e. require authentication),
          ensure that the attribute set to a value other than `None`.

        This will apply to both the local Buildarr configuration and
        the remote Prowlarr instance configuration.

        Args:
            value (Optional[str]): Value to validate
            values (Dict[str, Any]): Configuration attributes

        Raises:
            ValueError: If the attribute is required but empty

        Returns:
            Validated attribute value
        """
        if values["authentication"] == AuthenticationMethod.none:
            return None
        elif not value:
            raise ValueError("required when 'authentication' is not set to 'none'")
        return value


class ProxyGeneralSettings(GeneralSettings):
    """
    Proxy configuration for Prowlarr.
    """

    enable: bool = False
    """
    Use a proxy server to access the Internet.
    """

    proxy_type: ProxyType = ProxyType.http
    """
    Type of proxy to connect to.

    Values:

    * `http` - HTTP(S) proxy
    * `socks4` - SOCKSv4 proxy
    * `socks5` - SOCKSv5 proxy (Tor is supported)
    """

    # TODO: Enforce constraint
    hostname: Optional[str] = None
    """
    Proxy server hostname.

    Required if using a proxy is enabled.
    """

    port: Port = 8080  # type: ignore[assignment]
    """
    Proxy server access port.
    """

    username: Optional[str] = None
    """
    Username to authenticate with.
    Only enter if authentication is required by the proxy.
    """

    password: Optional[Password] = None
    """
    Password for the proxy user.
    Only enter if authentication is required by the proxy.
    """

    ignored_addresses: Set[NonEmptyStr] = set()
    """
    List of domains/addresses which bypass the proxy. Wildcards (`*`) are supported.
    """

    bypass_proxy_for_local_addresses: bool = True
    """
    Do not use the proxy to access local network addresses.
    """

    _remote_map: List[RemoteMapEntry] = [
        ("enable", "proxyEnabled", {}),
        ("proxy_type", "proxyType", {}),
        (
            "hostname",
            "proxyHostname",
            {"decoder": lambda v: v or None, "encoder": lambda v: v or ""},
        ),
        ("port", "proxyPort", {}),
        (
            "username",
            "proxyUsername",
            {"decoder": lambda v: v or None, "encoder": lambda v: v or ""},
        ),
        (
            "password",
            "proxyPassword",
            {
                "decoder": lambda v: v or None,
                "encoder": lambda v: v.get_secret_value() if v else "",
            },
        ),
        (
            "ignored_addresses",
            "proxyBypassFilter",
            {
                "decoder": lambda v: (
                    set(addr.strip() for addr in v.split(",")) if v and v.strip() else []
                ),
                "encoder": lambda v: ",".join(sorted(v)) if v else "",
            },
        ),
        ("bypass_proxy_for_local_addresses", "proxyBypassLocalAddresses", {}),
    ]


class LoggingGeneralSettings(GeneralSettings):
    """
    Logging configuration for the Prowlarr application.
    """

    log_level: ProwlarrLogLevel = ProwlarrLogLevel.INFO
    """
    Verbosity of logging output.

    Values:

    * `INFO` - Standard log output
    * `DEBUG` - Debugging log output
    * `TRACE` - Trace diagnostics log output
    """

    _remote_map: List[RemoteMapEntry] = [("log_level", "logLevel", {})]


class AnalyticsGeneralSettings(GeneralSettings):
    """
    Configuration of analytics and telemetry from within Prowlarr.
    """

    send_anonymous_usage_data: bool = True
    """
    Send anonymous usage and error information to Prowlarr's servers.

    This includes information on your browser, which Prowlarr Web UI pages you use,
    error reporting and OS/runtime versions. This information is reportedly used
    to prioritise features and bug fixes.

    Requires a restart of Prowlarr to take effect.
    """

    _remote_map: List[RemoteMapEntry] = [("send_anonymous_usage_data", "analyticsEnabled", {})]


class UpdatesGeneralSettings(GeneralSettings):
    """
    Settings for updating Prowlarr.
    """

    branch: NonEmptyStr = "master"  # type: ignore[assignment]
    """
    Branch used by the external update mechanism.
    Changing this value has no effect on Docker installations.

    If unsure, leave this undefined in Buildarr and use the value already set in Prowlarr.
    """

    automatic: bool = False
    """
    Automatically download and install updates.
    Manual updates can still be performed from System -> Updates.

    This option must be left set to `false` on Docker installations.
    """

    # script_path is required when mechanism is "script"
    # script_path should be absolute only
    mechanism: UpdateMechanism = UpdateMechanism.docker
    """
    Set the mechanism for updating Prowlarr.
    Must be set to `docker` on Docker installations.

    Values:

    * `builtin` - Prowlarr built-in updater mechanism
    * `script` - Use the configured update script
    * `external` - External update mechanism
    * `apt` - Debian APT package
    * `docker` - Docker image
    """

    # TODO: Constraint - required if update mechanism is "script"
    script_path: Optional[str] = None
    """
    Path to a custom script that takes an extracted update package
    and handles the remainder of the update process.

    Required if `mechanism` is set to `script`.
    """

    _remote_map: List[RemoteMapEntry] = [
        ("branch", "branch", {}),
        ("automatic", "updateAutomatically", {}),
        ("mechanism", "updateMechanism", {}),
        (
            "script_path",
            "updateScriptPath",
            {"decoder": lambda v: v or None, "encoder": lambda v: v or ""},
        ),
    ]


class BackupGeneralSettings(GeneralSettings):
    """
    Settings for Prowlarr automatic backups.
    """

    folder: NonEmptyStr = "Backups"  # type: ignore[assignment]
    """
    Folder to backup Prowlarr data to.

    Relative paths will be under Prowlarr's AppData directory.
    """

    interval: int = Field(7, ge=1, le=7)  # days
    """
    Interval between automatic backups, in days.

    Must be set somewhere between 1 and 7 days.
    """

    retention: int = Field(28, ge=1, le=90)  # days
    """
    Retention period for backups, in days.
    Backups older than the retention period will be cleaned up automatically.

    Must be set somewhere between 1 and 90 days.
    """

    _remote_map: List[RemoteMapEntry] = [
        ("folder", "backupFolder", {}),
        ("interval", "backupInterval", {}),
        ("retention", "backupRetention", {}),
    ]


class ProwlarrGeneralSettings(ProwlarrConfigBase):
    """
    Prowlarr general settings.
    """

    host: HostGeneralSettings = HostGeneralSettings()
    security: SecurityGeneralSettings = SecurityGeneralSettings()
    proxy: ProxyGeneralSettings = ProxyGeneralSettings()
    logging: LoggingGeneralSettings = LoggingGeneralSettings()
    analytics: AnalyticsGeneralSettings = AnalyticsGeneralSettings()
    updates: UpdatesGeneralSettings = UpdatesGeneralSettings()
    backup: BackupGeneralSettings = BackupGeneralSettings()

    @classmethod
    def from_remote(cls, secrets: ProwlarrSecrets) -> Self:
        with prowlarr_api_client(secrets=secrets) as api_client:
            remote_attrs = prowlarr.HostConfigApi(api_client).get_host_config().to_dict()
        return cls(
            host=HostGeneralSettings._from_remote(remote_attrs),
            security=SecurityGeneralSettings._from_remote(remote_attrs),
            proxy=ProxyGeneralSettings._from_remote(remote_attrs),
            logging=LoggingGeneralSettings._from_remote(remote_attrs),
            analytics=AnalyticsGeneralSettings._from_remote(remote_attrs),
            updates=UpdatesGeneralSettings._from_remote(remote_attrs),
            backup=BackupGeneralSettings._from_remote(remote_attrs),
        )

    def update_remote(
        self,
        tree: str,
        secrets: ProwlarrSecrets,
        remote: Self,
        check_unmanaged: bool = False,
    ) -> bool:
        host_updated, host_attrs = self.host._update_remote_attrs(
            tree=f"{tree}.host",
            secrets=secrets,
            remote=remote.host,
            check_unmanaged=check_unmanaged,
        )
        security_updated, security_attrs = self.security._update_remote_attrs(
            tree=f"{tree}.security",
            secrets=secrets,
            remote=remote.security,
            check_unmanaged=check_unmanaged,
        )
        proxy_updated, proxy_attrs = self.proxy._update_remote_attrs(
            tree=f"{tree}.proxy",
            secrets=secrets,
            remote=remote.proxy,
            check_unmanaged=check_unmanaged,
        )
        logging_updated, logging_attrs = self.logging._update_remote_attrs(
            tree=f"{tree}.logging",
            secrets=secrets,
            remote=remote.logging,
            check_unmanaged=check_unmanaged,
        )
        analytics_updated, analytics_attrs = self.analytics._update_remote_attrs(
            tree=f"{tree}.analytics",
            secrets=secrets,
            remote=remote.analytics,
            check_unmanaged=check_unmanaged,
        )
        updates_updated, updates_attrs = self.updates._update_remote_attrs(
            tree=f"{tree}.updates",
            secrets=secrets,
            remote=remote.updates,
            check_unmanaged=check_unmanaged,
        )
        backup_updated, backup_attrs = self.backup._update_remote_attrs(
            tree=f"{tree}.backup",
            secrets=secrets,
            remote=remote.backup,
            check_unmanaged=check_unmanaged,
        )
        if any(
            [
                host_updated,
                security_updated,
                proxy_updated,
                logging_updated,
                analytics_updated,
                updates_updated,
                backup_updated,
            ],
        ):
            with prowlarr_api_client(secrets=secrets) as api_client:
                host_config_api = prowlarr.HostConfigApi(api_client)
                remote_attrs = {
                    # There are some undocumented values that are not
                    # set by Buildarr. Pass those through unmodified.
                    **host_config_api.get_host_config().to_dict(),
                    **host_attrs,
                    **security_attrs,
                    **proxy_attrs,
                    **logging_attrs,
                    **analytics_attrs,
                    **updates_attrs,
                    **backup_attrs,
                }
                host_config_api.update_host_config(
                    id=str(remote_attrs["id"]),
                    host_config_resource=prowlarr.HostConfigResource.from_dict(remote_attrs),
                )
            return True
        return False
