# Indexer Proxies

##### ::: buildarr_prowlarr.config.settings.indexers.proxies.ProxiesSettings
    options:
      members:
        - delete_unmanaged
        - definitions

## Configuring indexer proxies

##### ::: buildarr_prowlarr.config.settings.indexers.proxies.Proxy
    options:
      members:
        - tags

## FlareSolverr

##### ::: buildarr_prowlarr.config.settings.indexers.proxies.FlaresolverrProxy
    options:
      members:
        - type
        - host_url
        - request_timeout

## HTTP proxy

##### ::: buildarr_prowlarr.config.settings.indexers.proxies.HttpProxy
    options:
      members:
        - type
        - hostname
        - port
        - username
        - password

## SOCKS4 proxy

##### ::: buildarr_prowlarr.config.settings.indexers.proxies.Socks4Proxy
    options:
      members:
        - type
        - hostname
        - port
        - username
        - password

## SOCKS5 proxy

##### ::: buildarr_prowlarr.config.settings.indexers.proxies.Socks5Proxy
    options:
      members:
        - type
        - hostname
        - port
        - username
        - password
