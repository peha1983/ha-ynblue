# Troubleshooting

## Login spins indefinitely or ends with an unknown error

YnBlue 0.3.1 contains a credential-validation deadlock that can leave the Home Assistant config flow waiting indefinitely even when the cloud responds. This is fixed in YnBlue 0.3.2.

What to do:

1. Upgrade to the v0.3.2 GitHub release through HACS when it is available.
2. Restart Home Assistant after upgrading.
3. Add YnBlue again from `Settings -> Devices & Services`.

After the fix, rejected credentials are shown as an authentication error and REST/network timeouts are shown as a connection error. If the YnBlue mobile app accepts the same account but Home Assistant still cannot connect on 0.3.2 or newer, collect redacted logs before opening an issue. Never publish the account email, password, or token.

YnBlue 0.3.2 requires Home Assistant 2026.6.4 or newer. HACS will enforce this declared minimum for the 0.3.2 release.

## Entities are unavailable after startup

What is normal:

- Metadata refresh starts within the first polling cycle.
- A full snapshot may take up to one refresh window after startup.

What to check:

1. Wait at least 90 seconds after startup or integration reload.
2. Check `binary_sensor.<device>_online`.
3. Press the `Request snapshot` button entity once.
4. Confirm the account credentials still work in the YnBlue mobile app.

If the controller is online in YnBlue but Home Assistant never gets a snapshot, collect logs and open an issue.

## Values are not unavailable but remain stale

Typical symptoms:

- the same pool temperature for many hours or days
- tank levels that do not move
- a controller that looks online but does not refresh live values

What to check:

1. Inspect `sensor.<device>_live_data_age_minutes`.
2. Inspect `sensor.<device>_last_cloud_contact`.
3. Press `Request snapshot`.
4. Reload the integration once.

Interpretation:

- If the live data age keeps increasing, the integration is preserving the last good snapshot on purpose.
- If the controller does not resume after a snapshot request and integration reload, the physical YnBlue controller may be hung.
- In that controller-hung state, restarting Home Assistant does not fix the upstream device. Restart the YnBlue controller itself.

## Tank level looks empty but the tank is not empty

This usually means the current value is stale or the upstream controller is not sending fresh liquid-level data.

Check:

- `binary_sensor.<device>_online`
- `sensor.<device>_live_data_age_minutes`
- whether a fresh snapshot arrives after `Request snapshot`

If the age sensor is stale, trust the freshness indicators more than the old tank value until the controller resumes reporting.

## Buttons or commands do not appear to work

Possible reasons:

- the relevant hardware feature is not enabled on that controller
- the controller is offline
- the command reached the cloud path but the post-command confirmation snapshot did not arrive

What to check:

1. Confirm the entity exists because the controller actually exposes that capability.
2. Confirm the online sensor is on.
3. Trigger the command and then inspect whether a new snapshot arrived.

If a command is supposed to be supported but repeatedly fails with the controller online, open an issue with logs and the exact entity used.

## Manual pH injection confirmation (v0.3.3 and later)

Starting with v0.3.3, the snapshot after a manual pH start or stop command must report the requested `pH.injection.state`: boolean `true` for start and boolean `false` for stop. A contradictory, missing, or malformed state raises a command error; strings, numbers, and `null` are not confirmation. In v0.3.2, these actions only require the follow-up snapshot to arrive and do not verify the reported injection state.

The integration sends each command once and does not automatically resend it when confirmation fails. The online and fresh-snapshot checks still run before sending a command.

Before starting a dose, the controller must report `filter.state: true`, with no active chemical injection (`chemical.injection` or `chemical.injectionExtra`) or existing manual pH injection. These checks run inside the per-controller command lock. A stop command does not require running filtration.

The official [YnBlue web app](https://app.yneom-iot.com/) also offers manual pH injection only while its own filtration state is running and the chemical dosing paths are inactive. Its start payload is the same `{"mode":2,"value":1}` used by this integration. If the pool pump is controlled externally, its physical operation alone does not update YnBlue's internal filtration state. Check the controller's filter configuration and the installation's wiring; do not automatically force a relay or bypass circulation requirements. The integration now explains this condition before sending an ineffective start command.

A confirmation error after sending a command does not prove that no liquid was dispensed. Check the current controller state and the equipment before retrying. A confirmed controller state also does not independently prove physical pump operation or delivered volume. The Home Assistant button timestamp records a press attempt, not successful dosing.

## HACS installation does not show the integration

YnBlue has been in the standard HACS integration catalog since July 2, 2026.

1. Refresh HACS data and search for `YnBlue` in the integration catalog.
2. Confirm HACS itself is up to date.
3. Download YnBlue and restart Home Assistant.
4. Hard-refresh or clear the browser cache if HACS does not update the visible repository list.

No custom repository entry is required. Existing custom-repository installations can continue to use the same GitHub releases.

## Upgrading through HACS

1. Read the repository release notes first.
2. Upgrade from a tagged release in HACS.
3. Restart Home Assistant after the upgrade.
4. If entities remain stale, press `Request snapshot` once before deeper troubleshooting.

## Collecting useful diagnostics

Please include:

- Home Assistant version
- YnBlue integration version
- whether install came from HACS or a manual copy
- relevant log lines
- values of:
  - `binary_sensor.<device>_online`
  - `sensor.<device>_last_cloud_contact`
  - `sensor.<device>_live_data_age_minutes`

Before sharing logs publicly, redact secrets and personal identifiers.

YnBlue 0.3.2 logs the first metadata or snapshot transport failure immediately, suppresses equivalent repeats for 30 minutes, then emits a summarized reminder if the failure continues. A successful refresh produces one recovery message and resets the suppression window. This behavior limits log noise without hiding failure/recovery transitions. Controller identifiers are replaced with labels such as `controller 1`.
