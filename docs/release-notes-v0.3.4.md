# YnBlue v0.3.4 release notes

## Added

- Weekly Dependabot checks for GitHub Actions. Repository security monitoring now includes Dependabot alerts and CodeQL for Python and GitHub Actions.

## Changed

- Validation and release packaging use Ubuntu 24.04. Daily validation is scheduled for 02:17 UTC; GitHub may delay scheduled runs.
- Validation explicitly uses read-only repository permissions.
- Release metadata and documentation are finalized before validating the release commit. Repeating the package publication workflow no longer overwrites an existing release asset.

## Fixed

- Changed the runtime dependency declaration from `paho-mqtt==2.1.0` to `paho-mqtt>=2.1.0`. This satisfies the updated hassfest rule for dependencies also used by Home Assistant and lets Home Assistant's dependency constraints select a compatible version.

## Breaking changes

- None. No configuration migration, entity rename, minimum Home Assistant version change, or controller-command behavior change.

## Upgrade notes

- Upgrade to `v0.3.4` in HACS, then restart Home Assistant. Existing account configuration, entities, and controller settings are retained.
- Home Assistant 2026.6.4 remains the minimum supported version. This update does not require upgrading Home Assistant or HACS.
- This maintenance release addresses dependency compatibility and validation. It does not repair physical pH probes or resolve independent vendor-cloud connectivity problems.
- To roll back on the validated Home Assistant versions, select `v0.3.3` in HACS and restart Home Assistant; no configuration migration is required.

## Validation

- All 84 tests pass locally on each of Home Assistant 2026.6.4 and 2026.8.1 with Python 3.14 and network sockets disabled. Ruff, dependency consistency, YAML parsing, and whitespace checks pass.
- Release gates cover both Home Assistant test lanes, hassfest, HACS validation, package construction, and CodeQL on the exact release commit.
- The release workflow checks tag/manifest agreement and publishes one `ynblue.zip` with integration files at the archive root.
- Automated validation uses synthetic controller data and issues no production dosing or actuator commands.
