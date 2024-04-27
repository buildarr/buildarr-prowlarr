# Applications

##### ::: buildarr_prowlarr.config.settings.apps.applications.ApplicationsSettings
    options:
      members:
        - delete_unmanaged
        - definitions

## Configuration

##### ::: buildarr_prowlarr.config.settings.apps.applications.Application
    options:
      members:
        - prowlarr_url
        - base_url
        - sync_level
        - sync_categories
        - tags

## LazyLibrarian

##### ::: buildarr_prowlarr.config.settings.apps.applications.LazylibrarianApplication
    options:
      members:
        - type
        - api_key
        - sync_categories

## Lidarr

##### ::: buildarr_prowlarr.config.settings.apps.applications.LidarrApplication
    options:
      members:
        - type
        - api_key
        - sync_categories

##### ::: buildarr_prowlarr.config.settings.apps.applications.ArrApplication
    options:
      members:
        - sync_reject_blocklisted_torrent_hashes

## Mylar

##### ::: buildarr_prowlarr.config.settings.apps.applications.MylarApplication
    options:
      members:
        - type
        - api_key
        - sync_categories

## Radarr

##### ::: buildarr_prowlarr.config.settings.apps.applications.RadarrApplication
    options:
      members:
        - type
        - instance_name
        - api_key
        - sync_categories

##### ::: buildarr_prowlarr.config.settings.apps.applications.ArrApplication
    options:
      members:
        - sync_reject_blocklisted_torrent_hashes

## Readarr

##### ::: buildarr_prowlarr.config.settings.apps.applications.ReadarrApplication
    options:
      members:
        - type
        - api_key
        - sync_categories

##### ::: buildarr_prowlarr.config.settings.apps.applications.ArrApplication
    options:
      members:
        - sync_reject_blocklisted_torrent_hashes

## Sonarr

##### ::: buildarr_prowlarr.config.settings.apps.applications.SonarrApplication
    options:
      members:
        - type
        - instance_name
        - api_key
        - sync_categories
        - anime_sync_categories
        - sync_anime_standard_format_search

##### ::: buildarr_prowlarr.config.settings.apps.applications.ArrApplication
    options:
      members:
        - sync_reject_blocklisted_torrent_hashes

## Whisparr

##### ::: buildarr_prowlarr.config.settings.apps.applications.WhisparrApplication
    options:
      members:
        - type
        - api_key
        - sync_categories

##### ::: buildarr_prowlarr.config.settings.apps.applications.ArrApplication
    options:
      members:
        - sync_reject_blocklisted_torrent_hashes
