# YnBlue v0.3.3 release notes

## Added

- Repeatable HACS ZIP packaging and automatic release-asset publication. Package download counters measure requests, not unique installations or users.
- Regression coverage for manual pH start/stop confirmation, malformed snapshots, command failures without retries, and concurrent starts.

## Changed

- Manual pH actions report success only when a follow-up snapshot contains the requested boolean `pH.injection.state`.
- Documentation links to the current official YnBlue web application and explains externally controlled filtration.

## Fixed

- Manual pH start now checks controller-reported running filtration and rejects active chemical dosing or an already active pH injection before publishing. These checks run under the per-controller command lock.
- Opposite, missing, or malformed injection states now raise a command error instead of reporting a successful start or stop.
- Stop remains available independently of the start conditions, subject to the existing online and fresh-snapshot checks.

## Breaking changes

- No entity renames, configuration migrations, or minimum Home Assistant version changes.
- Automations may now receive an error when filtration is not reported as running or the requested injection state cannot be confirmed.

## Upgrade notes

- Upgrade to `v0.3.3` in HACS, then restart Home Assistant. Existing configuration and entities are retained.
- An externally operated pool pump does not automatically update YnBlue's filtration state. Check controller configuration and wiring; this release does not force filtration or synchronize external pumps.
- Commands are sent once and are never automatically retried. A confirmation error does not prove that no liquid was dispensed; check the controller and equipment before retrying.
- Controller confirmation does not independently verify physical flow or delivered volume. A button timestamp records a press attempt, not successful dosing.
- To roll back, select `v0.3.2` in HACS and restart Home Assistant; no configuration migration is required.

## Validation

- All 84 tests pass locally on each of Home Assistant 2026.6.4 and 2026.8.1 with Python 3.14 and network access disabled; Ruff and whitespace checks also pass.
- The exact release commit is gated by the `Validate` workflow: both Home Assistant test lanes, hassfest, HACS validation, and HACS package construction.
- The `Publish HACS package` workflow validates tag/manifest agreement and attaches one `ynblue.zip` with integration files at the archive root.
- Validation uses synthetic controller data. No production installation, restart, or dosing command is part of this release validation.
