# Support

## Before opening an issue

Please work through these steps first:

1. Read the [troubleshooting guide](docs/troubleshooting.md).
2. Confirm the installed version in HACS matches the latest tagged release you expect.
3. Check the entity health indicators:
   - `binary_sensor.<device>_online`
   - `sensor.<device>_last_cloud_contact`
   - `sensor.<device>_live_data_age_minutes`
4. Trigger the `Request snapshot` button entity once and wait for one refresh cycle.
5. If the controller appears hung and values stay stale, restart the physical YnBlue controller. Reloading Home Assistant alone cannot recover a controller that has stopped talking to the YnBlue cloud.

## When to open a bug report

Open an issue when:

- data stays stale after the controller is back online
- entities remain unavailable after a full refresh cycle
- a supported command consistently fails
- HACS installation or upgrade behavior is broken

## What to include

- Home Assistant version
- YnBlue integration version
- installation source: HACS custom repository or local manual copy
- controller product or model name if known
- exact symptom
- steps to reproduce
- redacted log excerpts
- whether the controller came back only after a physical reboot

## Sensitive information

Do not post:

- email addresses
- passwords
- access tokens
- MQTT credentials
- exact home address or GPS data
- raw diagnostics that still contain personal information
