# Release Notes (Buildarr Prowlarr Plugin)

## [v0.5.3](https://github.com/buildarr/buildarr-prowlarr/releases/tag/v0.5.3) - 2024-04-29

This release contains fixes for issues resulting from backward-incompatible changes to the Prowlarr API.

* Add the `sync_reject_blocklisted_torrent_hashes` attribute to the Lidarr, Radarr, Readarr, Sonarr and Whisparr application definitions (available in Prowlarr v1.15 and above).
* Add the `always`, `preferred` and `never` options to the `use_encryption` attribute on email notification connections.
    * In version 0.5.2 and below of the plugin, `true` and `false` values were used when defining this attribute. In older versions of Prowlarr, these values used to correspond to `always` and `preferred`, respectively. `true` and `false` can still be used, but in newer versions of Prowlarr, `false` now corresponds to `never`.
    * `never` is available in Prowlarr v1.13 and above. If `never` is selected on an older version, it will result in `preferred` being used.
* Make sure the Prowlarr plugin does not raise an error when new (unimplemented) resource attributes are found, and instead ensure they are passed through without modification. This ensures that backwards-compatible API additions do not cause any problems when using Buildarr with newer versions of Prowlarr.

In addition, the following issues were resolved:

* Loosen Pushover user/API key constraints, to allow Pushover notification connections to be managed following the change to Prowlarr to obfuscate secret values in API responses.

### Changed

* Fix compatibility with newer versions of Prowlarr ([#66](https://github.com/buildarr/buildarr-prowlarr/pull/66))


## [v0.5.2](https://github.com/buildarr/buildarr-prowlarr/releases/tag/v0.5.2) - 2024-04-26

This release contains mitigations for an issue where on newer versions of Prowlarr,
secret values are obfuscated in API responses to avoid exposing them on insecure applications.

In the best case scenario, they cause Buildarr to always re-apply the configuration for a resource,
as they always report as "changed".
In the worst case scenario, the obfuscated values violate strict value constraints set in Buildarr,
causing errors to occur when fetching remote instance configurations.

The fixes in this release resolve this worst case scenario.

A more permanent fix for handling this problem in general
is planned for future releases of Buildarr.

### Changed

* Loosen secret value constraints ([#61](https://github.com/buildarr/buildarr-prowlarr/pull/61))


## [v0.5.1](https://github.com/buildarr/buildarr-prowlarr/releases/tag/v0.5.1) - 2023-12-02

This release adds the following new features:

* Support defining a URL base for the Prowlarr instance in the Buildarr configuration, using the `url_base` host configuration attribute.
    * This allows Prowlarr instances with APIs available under a custom path (e.g. `http://localhost:9696/prowlarr`) to be managed by Buildarr.
* Add support for auto-fetching the Prowlarr API key when dumping instance configurations, by pressing the Enter key without specifying an API key when prompted.
    * This brings the Prowlarr plugin in line with other Buildarr plugins which already support this.
* Add support for auto-fetching the Prowlarr API key from newer versions of Prowlarr which use the `initialize.json` endpoint.

The following issues have also been fixed:

* Use the Buildarr-global API request timeout setting as the timeout for Prowlarr API requests, instead of not using a timeout.

### Changed

* Add Prowlarr instance URL base support ([#54](https://github.com/buildarr/buildarr-prowlarr/pull/54))


## [v0.5.0](https://github.com/buildarr/buildarr-prowlarr/releases/tag/v0.5.0) - 2023-11-12

This updates the Prowlarr plugin so that it is compatible with [Buildarr v0.7.0](https://buildarr.github.io/release-notes/#v070-2023-11-12).

### Changed

* Add Buildarr v0.7.0 support ([#48](https://github.com/buildarr/buildarr-prowlarr/pull/48))


## [v0.4.3](https://github.com/buildarr/buildarr-prowlarr/releases/tag/v0.4.3) - 2023-11-07

This release fixes the following issues:

* Fix a username/password related parsing error when the authentication method is not explicitly defined in the Buildarr configuration

### Changed

* Remove validation for username/password ([#44](https://github.com/buildarr/buildarr-prowlarr/pull/44))


## [v0.4.2](https://github.com/buildarr/buildarr-prowlarr/releases/tag/v0.4.2) - 2023-11-07

This release adds support for the `external` authentication method for Prowlarr, and makes it possible for Buildarr to manage Prowlarr instances configured to use the `external` authentication method.

This authentication method is usually only accessible by manually modifying the Prowlarr configuration file, but Buildarr makes it possible to configure it automatically.

The following issues have also been fixed:

* Fix a regression in the previous release where new application definitions could not be created
* Remove support for the `none` authentication method, no longer usable in Prowlarr v1.0 and later

### Added

* Add support for external authentication ([#37](https://github.com/buildarr/buildarr-prowlarr/pull/37))

### Changed

* FIx creating application definitions ([#39](https://github.com/buildarr/buildarr-prowlarr/pull/39))
* Fix Sonarr/Radarr plugin links in docs ([#40](https://github.com/buildarr/buildarr-prowlarr/pull/40))

### Removed

* Remove support for no authentication ([#38](https://github.com/buildarr/buildarr-prowlarr/pull/38))


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
