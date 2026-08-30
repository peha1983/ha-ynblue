# YnBlue v0.3.2 release notes

## Added

- Dedicated CI compatibility lanes for Home Assistant 2026.6.4 and 2026.8.1.

## Changed

- Equivalent metadata and snapshot transport warnings are emitted immediately, then summarized at most every 30 minutes while the failure continues. Recovery remains a one-time state-transition message.
- Runtime warnings, transport errors, and diagnostics mapping keys no longer expose cloud controller identifiers.
- The supported minimum Home Assistant version is now 2026.6.4, the oldest version backed by the release's live validation and CI strategy.
- YnBlue is installed from the standard HACS integration catalog; it has been listed there since July 2, 2026.

## Fixed

- Fixed the credential-validation lock cycle that could leave initial setup or reauthentication spinning indefinitely.
- Removed upstream response bodies from surfaced API error messages.

## Breaking changes

- Home Assistant versions older than 2026.6.4 are no longer declared compatible with YnBlue 0.3.2 because the previous 2025.12.0 minimum lacked current validation evidence.

## Upgrade notes

- Upgrade to the tagged `v0.3.2` release in HACS, then restart Home Assistant.
- Existing YnBlue config entries and entities are retained; no account reconfiguration or migration is required.
- If setup was left spinning on 0.3.1, close that flow, upgrade and restart, then add YnBlue again. An already configured account will stop promptly with Home Assistant's `already_configured` result.
- HACS cannot offer 0.3.2 until the matching GitHub release is published. Do not install an arbitrary `main` snapshot as a substitute for the release.

## Validation

- Redacted live smoke gate passed on Home Assistant 2026.6.4 and HACS 2.0.5: existing-entry startup, duplicate-account setup handling, snapshot refresh, controlled restarts, clean boot and rollback all completed successfully. No physical commands were issued.
- Automated regression basis: Home Assistant 2026.8.1 and Python 3.14.
- The exact release commit is gated by both test matrix lanes, hassfest and HACS validation in the `Validate` workflow.

## HACS release path

The Git tag and full GitHub release are both named `v0.3.2` and point to the exact validated commit. The repository is already present in the standard HACS catalog, `hacs.json` declares the minimum Home Assistant version, and `custom_components/ynblue/manifest.json` declares version `0.3.2`; HACS discovers the GitHub release as the upgrade source.
