# Release Notes (Buildarr Prowlarr Plugin)

## [v0.3.0](https://github.com/buildarr/buildarr-prowlarr/releases/tag/v0.3.0) - 2023-09-09

This updates the Prowlarr plugin so that it is compatible with [Buildarr v0.6.0](https://buildarr.github.io/release-notes/#v060-2023-09-02).
This version is also backwards compatible with [Buildarr v0.5.0](https://buildarr.github.io/release-notes/#v050-2023-04-16).

Other changes to the Prowlarr plugin for this release include:

* Relax URL parsing on the `buildarr prowlarr dump-config` command, fixing configuration dumping from Prowlarr instances without a canonical domain name (e.g. IP addresses and `localhost`)

### Changed

* Update package metadata and dependencies ([#15](https://github.com/buildarr/buildarr-prowlarr/pull/15))


## [v0.2.0](https://github.com/buildarr/buildarr-prowlarr/releases/tag/v0.2.0) - 2023-04-16

This updates the Prowlarr plugin so that it is compatible with [Buildarr v0.5.0](https://buildarr.github.io/release-notes/#v050-2023-04-16).

Other changes to the Prowlarr plugin for this release include:

* Rename the Freebox download client `priority` attribute to `client_priority` (same as other download client types), as it was shadowing the Prowlarr-oriented `priority` attribute (common to all download clients), and giving incorrect values for both attributes
* Improve support for deleting resources with `delete_unmanaged`, by using the new `delete_remote` API function
* Remove the `prowlarr.tags.delete_unused` attribute (for deleting Prowlarr tags not used in Buildarr), as it was unimplemented and Prowlarr automatically cleans up unused tags anyway

### Changed

* Update plugin to newer Buildarr API standards ([#10](https://github.com/buildarr/buildarr-prowlarr/pull/10))


## [v0.1.1](https://github.com/buildarr/buildarr-prowlarr/releases/tag/v0.1.1) - 2023-04-08

This is a bugfix release to resolve problems with the first release, particularly when using Prowlarr to manage the indexers of Sonarr instances.

* Add an error message for when an invalid indexer type is provided
* Add mutual exclusion handling for the `category` and `directory` attributes in Transmission/Vuze download clients
* Fix updating app sync profiles
* Fix updating indexer proxies, download clients, application links and app sync profiles when not all type-specific resource values are defined in the configuration
* Require at least [version 0.4.1](https://buildarr.github.io/plugins/sonarr/release-notes/#v041-2023-04-08) of the Sonarr plugin for Buildarr, to fix bugs with instance linking

### Changed

* Fix bugs from integration tests ([#4](https://github.com/buildarr/buildarr-prowlarr/pull/4))


## [v0.1.0](https://github.com/buildarr/buildarr-prowlarr/releases/tag/v0.1.0) - 2023-04-08

First release of the Prowlarr plugin for Buildarr.
