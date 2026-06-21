# Troubleshooting

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

## HACS installation does not show the integration

1. Confirm the repository URL is `https://github.com/peha1983/ha-ynblue`.
2. Add it as type `Integration`.
3. Restart Home Assistant after install.
4. Hard-refresh or clear the browser cache if HACS does not update the visible repository list.

Official HACS default listing is still pending upstream review. Until then, install this repository as a HACS custom repository.

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
