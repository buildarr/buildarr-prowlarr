# Release Notes (Buildarr Prowlarr Plugin)

## [v0.4.1](https://github.com/buildarr/buildarr-prowlarr/releases/tag/v0.4.1) - 2023-11-05

This release fixes the following issues:

* Fix indexer URL handling, so indexers with explicitly defined base URLs (instead of using the default) can be managed

### Changed

* Fix indexer URL field handling ([#31](https://github.com/buildarr/buildarr-prowlarr/pull/31))


## [v0.4.0](https://github.com/buildarr/buildarr-prowlarr/releases/tag/v0.4.0) - 2023-11-05

This version changes the dependency requirements so that it now requires:

* [Buildarr v0.6.1](https://buildarr.github.io/release-notes/#v061-2023-09-11) or later (to fix a bug with email handling)
* [Sonarr plugin for Buildarr v0.5.1](https://buildarr.github.io/plugins/sonarr/release-notes/#v051-2023-09-09) or later (for Buildarr v0.6.0 support)

Buildarr v0.5.0 is no longer supported.

Other changes to the Prowlarr plugin for this release include:

* Add support for defining and managing the `sync_anime_standard_format_search` parameter for Sonarr applications (previously unmanaged)
* Allow category groups (e.g. `TV`, `Movies`) to be defined in `sync_categories` to allow all categories under a group for applications

### Changed

* Fix application profile sync category and paramater issues ([#27](https://github.com/buildarr/buildarr-prowlarr/pull/27))
* Update Buildarr version requirements ([#28](https://github.com/buildarr/buildarr-prowlarr/pull/28))


## [v0.3.1](https://github.com/buildarr/buildarr-prowlarr/releases/tag/v0.3.1) - 2023-09-09

This release implements instance links to Radarr instances in application definitions, using the `instance_name` attribute, similar to the existing Sonarr instance links.

This takes advantage of the new [Radarr plugin for Buildarr](https://buildarr.github.io/plugins/radarr), and allows users to add Radarr instances to Prowlarr configuration without having to explicitly pass the API key (as long as the Radarr instance itself is also configured by Buildarr).

### Added

* Implement instance links with Radarr instances ([#20](https://github.com/buildarr/buildarr-prowlarr/pull/20))

### Changed

* Directly parse URL in the CLI command ([#21](https://github.com/buildarr/buildarr-prowlarr/pull/21))


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
