# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog and the versioning used by this repository follows tagged GitHub releases.

## [0.3.2] - 2026-08-30

### Added

- Repository support assets for HACS users, maintainers, and contributors

### Changed

- Expanded README installation, support, and product-context documentation
- Updated installation guidance to reflect inclusion in the default HACS catalog on July 2, 2026
- Added CI lanes for the live-validated minimum Home Assistant 2026.6.4 and the reported login-regression basis 2026.8.1, both on Python 3.14
- Raised the declared minimum Home Assistant version from an unverified 2025.12.0 to the live-validated 2026.6.4 baseline
- Throttled equivalent metadata and snapshot transport warnings to one immediate warning and at most one summarized reminder every 30 minutes while retaining one-time recovery logs
- Redacted controller identifiers from runtime warnings, transport errors, and diagnostic mapping keys

### Fixed

- Fixed a credential-validation deadlock that caused initial login and reauthentication to spin indefinitely
- Removed raw controller identifiers and upstream response bodies from surfaced REST and MQTT error text

### Tests

- Added regression coverage for the authentication lock, config-flow authentication/timeout errors, warning throttling and recovery, and controller-identifier redaction
- Passed a redacted live smoke test on Home Assistant 2026.6.4 with HACS 2.0.5, including existing-entry startup, duplicate-account config flow, snapshot refresh, controlled restarts, and rollback; no physical commands were issued

## [0.3.1] - 2026-06-21

### Fixed

- Hardened YnBlue REST timeout handling
- Kept cached metadata active when cloud refresh times out
- Normalized MQTT connect failures into YnBlue runtime errors

### Tests

- Added regression coverage for timeout handling and snapshot connect failures

## [0.3.0] - 2026-05-21

### Added

- Diagnostic sensor `sensor.ynblue_live_data_age_minutes`

### Changed

- Improved stale live data detection and exposed freshness explicitly
- Backed off repeated snapshot retries instead of hammering the broker
- Switched runtime scheduling to Home Assistant native interval and call-later timers for cleaner reloads

### Fixed

- Reported controller online state based on fresh live data rather than metadata alone
- Hardened command safety when live data is stale

## [0.2.1] - 2026-05-04

### Fixed

- Added `recorder` as an `after_dependency` for hassfest compliance
- Corrected `iot_class` to `cloud_polling`
- Sorted `manifest.json` keys to satisfy Home Assistant validation

## [0.2.0] - 2026-05-04

### Changed

- Reworked the runtime around periodic metadata polling and short-lived MQTT snapshots
- Added automatic recovery after Home Assistant restarts and YnBlue reconnects
- Hardened command validation, diagnostics redaction, and per-device command serialization

### Added

- Product, architecture, and security documentation
- Expanded automated coverage to 20 tests

## [0.1.0] - 2026-05-02

### Added

- Native Home Assistant custom integration with config flow for YnBlue cloud accounts
- MQTT-backed sensors, binary sensors, numbers, selects, switches, lights, and action buttons
- HACS-ready repository structure, brand assets, validation workflow, and automated tests
- Initial validation against a live YnBlue controller and Home Assistant instance
