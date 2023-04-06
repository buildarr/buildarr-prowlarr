# Buildarr Prowlarr Plugin

[![PyPI](https://img.shields.io/pypi/v/buildarr-prowlarr)](https://pypi.org/project/buildarr-prowlarr) ![PyPI - Python Version](https://img.shields.io/pypi/pyversions/buildarr-prowlarr)  [![GitHub](https://img.shields.io/github/license/buildarr/buildarr-prowlarr)](https://github.com/buildarr/buildarr-prowlarr/blob/main/LICENSE) ![Pre-commit hooks](https://github.com/buildarr/buildarr-prowlarr/actions/workflows/pre-commit.yml/badge.svg) [![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

The Buildarr Prowlarr plugin (`buildarr-prowlarr`) is a plugin for Buildarr that adds the capability to configure and manage [Prowlarr](http://prowlarr.com) instances.

Prowlarr is a manager/proxy for *Arr application Usenet and Torrent indexers. It handles communication with individual indexers for multiple instances on their behalf from a single client, allowing easier configuration of indexers by only setting them up once, and better management of traffic going to indexers to reduce the risk of running into rate limits.

## Installation

When using Buildarr as a [standalone application](https://buildarr.github.io/installation/#standalone-application), the Prowlarr plugin can simply be installed using `pip`:

```bash
$ pip install buildarr buildarr-prowlarr
```

If you are linking a Prowlarr instance with another Buildarr-configured Sonarr instance, use the `sonarr` extra to also install a compatible version of the Sonarr plugin.

```bash
$ pip install buildarr buildarr-prowlarr[sonarr]
```

When using Buildarr as a [Docker container](https://buildarr.github.io/installation/#docker), the Prowlarr plugin is bundled with the official container (`callum027/buildarr`), so there is no need to install it separately.

You can upgrade, or pin the version of the plugin to a specific version, within the container by setting the `$BUILDARR_INSTALL_PACKAGES` environment variable in the `docker run` command using `--env`/`-e`:

```bash
-e BUILDARR_INSTALL_PACKAGES="buildarr-prowlarr==<version>"
```

## Quick Start

To use the Prowlarr plugin, create a `prowlarr` block within `buildarr.yml`, and enter the connection information required for the Buildarr instance to connect to the Prowlarr instance you'd like to manage.

Buildarr won't modify anything yet since no configuration has been defined, but you are able to test if Buildarr is able to connect to and authenticate with the Prowlarr instance.

```yaml
---

buildarr:
  watch_config: true

prowlarr:
  hostname: "localhost" # Defaults to `prowlarr`, or the instance name for instance-specific configs.
  port: 9696 # Defaults to 9696.
  protocol: "http" # Defaults to `http`.
  api_key: "..." # Optional. If undefined, auto-fetch (authentication must be disabled).
```

Now try a `buildarr run`. If the output is similar to the below output, Buildarr was able to connect to your Prowlarr instance.

```text
2023-03-29 20:39:50,856 buildarr:1 buildarr.cli.run [INFO] Buildarr version 0.4.0 (log level: INFO)
2023-03-29 20:39:50,856 buildarr:1 buildarr.cli.run [INFO] Loading configuration file '/config/buildarr.yml'
2023-03-29 20:39:50,872 buildarr:1 buildarr.cli.run [INFO] Finished loading configuration file
2023-03-29 20:39:50,874 buildarr:1 buildarr.cli.run [INFO] Loaded plugins: prowlarr (0.1.0)
2023-03-29 20:39:50,875 buildarr:1 buildarr.cli.run [INFO] Loading instance configurations
2023-03-29 20:39:50,877 buildarr:1 buildarr.cli.run [INFO] Finished loading instance configurations
2023-03-29 20:39:50,877 buildarr:1 buildarr.cli.run [INFO] Running with plugins: prowlarr
2023-03-29 20:39:50,877 buildarr:1 buildarr.cli.run [INFO] Resolving instance dependencies
2023-03-29 20:39:50,877 buildarr:1 buildarr.cli.run [INFO] Finished resolving instance dependencies
2023-03-29 20:39:50,877 buildarr:1 buildarr.cli.run [INFO] Loading secrets file from '/config/secrets.json'
2023-03-29 20:39:50,886 buildarr:1 buildarr.cli.run [INFO] Finished loading secrets file
2023-03-29 20:39:50,886 buildarr:1 buildarr.cli.run [INFO] <prowlarr> (default) Checking secrets
2023-03-29 20:39:50,912 buildarr:1 buildarr.cli.run [INFO] <prowlarr> (default) Connection test successful using cached secrets
2023-03-29 20:39:50,912 buildarr:1 buildarr.cli.run [INFO] <prowlarr> (default) Finished checking secrets
2023-03-29 20:39:50,912 buildarr:1 buildarr.cli.run [INFO] Saving updated secrets file to '/config/secrets.json'
2023-03-29 20:39:50,914 buildarr:1 buildarr.cli.run [INFO] Finished saving updated secrets file
2023-03-29 20:39:50,914 buildarr:1 buildarr.cli.run [INFO] Updating configuration on remote instances
2023-03-29 20:39:50,914 buildarr:1 buildarr.cli.run [INFO] <prowlarr> (default) Getting remote configuration
2023-03-29 20:39:51,406 buildarr:1 buildarr.cli.run [INFO] <prowlarr> (default) Finished getting remote configuration
2023-03-29 20:39:51,463 buildarr:1 buildarr.cli.run [INFO] <prowlarr> (default) Updating remote configuration
2023-03-29 20:39:52,019 buildarr:1 buildarr.cli.run [INFO] <prowlarr> (default) Remote configuration is up to date
2023-03-29 20:39:52,019 buildarr:1 buildarr.cli.run [INFO] <prowlarr> (default) Finished updating remote configuration
2023-03-29 20:39:52,019 buildarr:1 buildarr.cli.run [INFO] Finished updating configuration on remote instances
```

## Configuring your Buildarr instance

The following sections cover comprehensive configuration of a Prowlarr instance.

Note that these documents do not show how you *should* configure a Prowlarr instance. Rather, they show how you *can* configure a Prowlarr instance the way you want with Buildarr. For more information on how to optimally configure Prowlarr, you can refer to the excellent guides from [WikiArr](https://wiki.servarr.com/prowlarr) and [TRaSH-Guides](https://trash-guides.info/Prowlarr/).

* [Host Configuration](configuration/host.md)
* Settings:
    * Indexers:
        * [Indexers](configuration/settings/indexers/indexers.md)
        * [Proxies](configuration/settings/indexers/proxies.md)
    * Apps:
        * [Applications](configuration/settings/apps/applications.md)
        * [Sync Profiles](configuration/settings/apps/sync-profiles.md)
    * [Download Clients](configuration/settings/download-clients.md)
    * [Notifications](configuration/settings/notifications.md)
    * [Tags](configuration/settings/tags.md)
    * [General](prowlarr/configuration/settings/general.md)
    * [UI](prowlarr/configuration/settings/ui.md)

## Dumping an existing Prowlarr instance configuration

Buildarr is capable of dumping a running Prowlarr instance's configuration.

```bash
$ buildarr prowlarr dump-config http://localhost:9696 > prowlarr.yml
Prowlarr instance API key: <Paste API key here>
```

The dumped YAML object can be placed directly under the `prowlarr` configuration block, or used as an [instance-specific configuration](https://buildarr.github.io/configuration/#multiple-instances-of-the-same-type).

All possible values are explicitly defined in this dumped configuration.

```yaml
api_key: 1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d
hostname: localhost
image: lscr.io/linuxserver/prowlarr
port: 9696
protocol: http
settings:
  apps:
    applications:
      definitions:
        Radarr (4K):
          api_key: 1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d
          base_url: http://radarr-4k:7878
          prowlarr_url: http://prowlarr:9696
          sync_categories:
          - movies/uhd
          - movies/web-dl
          - movies/dvd
          - movies/hd
          - movies/other
          - movies/sd
          - movies/foreign
          - movies/3d
          - movies/bluray
          sync_level: add-and-remove-only
          tags: []
          type: radarr
        Radarr (HD):
          api_key: 1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d
          base_url: http://radarr-hd:7878
          prowlarr_url: http://prowlarr:9696
          sync_categories:
          - movies/uhd
          - movies/web-dl
          - movies/dvd
          - movies/hd
          - movies/other
          - movies/sd
          - movies/foreign
          - movies/3d
          - movies/bluray
          sync_level: add-and-remove-only
          tags: []
          type: radarr
      delete_unmanaged: false
    sync_profiles:
      definitions:
        Standard:
          enable_automatic_search: true
          enable_interactive_search: true
          enable_rss: true
          minimum_seeders: 1
      delete_unmanaged: false
  download_clients:
    definitions:
      Transmission:
        add_paused: false
        category: null
        client_priority: last
        directory: null
        enable: true
        host: transmission
        password: null
        port: 9091
        priority: 1
        tags: []
        type: transmission
        url_base: /transmission/
        use_ssl: false
        username: null
    delete_unmanaged: false
  general:
    analytics:
      send_anonymous_usage_data: true
    backup:
      folder: Backups
      interval: 7
      retention: 28
    host:
      bind_address: '*'
      instance_name: Prowlarr (Buildarr Example)
      port: 9696
      ssl_port: 6969
      url_base: null
      use_ssl: false
    logging:
      log_level: INFO
    proxy:
      bypass_proxy_for_local_addresses: true
      enable: false
      hostname: null
      ignored_addresses: []
      password: null
      port: 8080
      proxy_type: http
      username: null
    security:
      authentication: none
      certificate_validation: enabled
      password: null
      username: null
    updates:
      automatic: false
      branch: develop
      mechanism: docker
      script_path: null
  indexers:
    indexers:
      definitions:
        1337x:
          enable: false
          fields:
            baseUrl: null
            definitionFile: 1337x
            downloadlink: iTorrents.org
            downloadlink2: magnet
            sort: created
            torrentBaseSettings.seedRatio: null
            torrentBaseSettings.seedTime: null
            type: desc
          grab_limit: null
          indexer_priority: 1
          query_limit: null
          redirect: false
          secret_fields: {}
          sync_profile: Standard
          tags: []
          type: 1337x
        Nyaa.si:
          enable: false
          fields:
            baseUrl: null
            cat-id: All categories
            definitionFile: nyaasi
            filter-id: No filter
            prefer_magnet_links: true
            sort: created
            torrentBaseSettings.seedRatio: null
            torrentBaseSettings.seedTime: null
            type: desc
          grab_limit: 5
          indexer_priority: 2
          query_limit: 5
          redirect: false
          secret_fields: {}
          sync_profile: Standard
          tags:
          - anime
          type: nyaasi
      delete_unmanaged: false
    proxies:
      definitions:
        FlareSolverr:
          host_url: http://flaresolverr:8191/
          request_timeout: 60.0
          tags:
          - anime
          type: flaresolverr
      delete_unmanaged: false
  notifications:
    definitions: {}
    delete_unmanaged: false
  tags:
    definitions:
    - anime
    delete_unused: false
  ui:
    enable_color_impaired_mode: false
    first_day_of_week: sunday
    long_date_format: day-first
    short_date_format: word-month-first
    show_relative_dates: true
    theme: light
    time_format: twelve-hour
    ui_language: en
    week_column_header: month-first
version: 0.4.9.2083
```
