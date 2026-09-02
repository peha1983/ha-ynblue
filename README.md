# YnBlue for Home Assistant

![Validate](https://github.com/peha1983/ha-ynblue/actions/workflows/validate.yml/badge.svg)
![GitHub Release](https://img.shields.io/github/v/release/peha1983/ha-ynblue?display_name=tag&sort=semver)
![HACS Default](https://img.shields.io/badge/HACS-Default-41BDF5.svg)
![HACS package requests](https://img.shields.io/github/downloads/peha1983/ha-ynblue/total?label=HACS%20package%20requests)
[![Open your Home Assistant instance and open the YnBlue repository inside HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?category=integration&owner=peha1983&repository=ha-ynblue)

`ynblue` is a Home Assistant custom integration for YNEOM/YnBlue pool controllers.

It signs in to the YnBlue cloud, refreshes the JWT automatically, polls controller metadata, and uses short-lived MQTT snapshot sessions to expose live entities in Home Assistant.

## What Is YnBlue?

YnBlue is YNEOM's connected pool control platform for residential pools. According to the official [YNEOM product](https://www.yneom.com/en/connected-pool/), [FAQ](https://www.yneom.com/en/faq/), and [app documentation](https://www.yneom.com/en/ynblue-app/), the upstream system covers automated filtration, automatic pH correction, water treatment management, alerts, and optional control of connected equipment such as heating, lighting, and robotic cleaners.

The native YnBlue ecosystem is managed through the YnBlue mobile app and the `control.yneom-iot.com` web application documented by YNEOM. This integration brings that same controller fleet into Home Assistant with native entities, recovery logic, and automation-friendly state handling.

## Quick Start

1. Open HACS and search for `YnBlue` in the standard integration catalog.
2. Download `YnBlue`.
3. Restart Home Assistant.
4. Add `YnBlue` from `Settings -> Devices & Services`.
5. Sign in with the same YnBlue cloud account you use in the YnBlue mobile app.

YnBlue has been part of the default HACS integration catalog since July 2, 2026. Adding this repository as a custom repository is no longer required.

## What This Integration Adds

- One Home Assistant config entry per YnBlue cloud account, with automatic discovery of all linked controllers
- Native Home Assistant entities for telemetry, online state, freshness, setpoints, and supported outputs
- Safe command execution with follow-up snapshot confirmation for supported write actions
- Recovery behavior that preserves the last known good values while a controller or the cloud is temporarily unavailable

## Data Flow Overview

```text
YnBlue controller
  -> YNEOM cloud REST metadata
  -> YnBlue cloud MQTT snapshots and commands
  -> Home Assistant YnBlue integration
  -> Home Assistant entities, automations, dashboards, and alerts
```

## Supported Capabilities

Entities are created only when the controller reports the relevant hardware capability or port as enabled.

- Water quality and inventory: water temperature, measured pH, measured chemical value, estimated chemical value, pH tank level, chemical tank level, Wi-Fi RSSI, last cloud contact, and live data age
- Health and activity: online state, filter running, heater running, electrolyser running, sensor fault indicators, weather data availability, and force-measurement state
- Setpoints and operating modes: pool volume, pH target, chemical target, heater target, filter mode, heater mode, chemical mode, pH mode, and electrolyser protection mode
- Equipment control: light, secondary light, RGB light, robot, swim jet, fountain, auxiliary relays, and electrolyser temperature protection when exposed by the controller
- Service actions: snapshot refresh, force measurement, controller restart, RGB program cycle, pH injection, stop pH injection, and consumption reset actions

## Architecture And Limits

- The integration uses the official YnBlue cloud API and MQTT endpoints exposed by the vendor platform
- In the tested environment, the controller did not expose a local LAN API that Home Assistant could use directly
- YnBlue cloud credentials are required
- Live values are refreshed from short-lived MQTT snapshot sessions instead of a long-lived broker connection because this model has proven more reliable with YnBlue devices
- When the controller is offline, Home Assistant keeps the last confirmed values visible and exposes online/freshness state separately

## Runtime behavior

- Metadata refresh runs every 30 seconds.
- Full controller snapshots run every 90 seconds while the controller is online.
- A controller coming back online triggers an immediate snapshot refresh.
- Safe commands are confirmed with a follow-up snapshot before Home Assistant reports success.
- REST and MQTT timeout conditions degrade gracefully to cached state instead of crashing the runtime loop.
- The first metadata or snapshot transport failure is logged immediately. Equivalent repeats are summarized at most every 30 minutes, and recovery is logged once.
- Runtime warnings use redacted controller labels rather than cloud device identifiers.

## Installation

### HACS

1. Open HACS.
2. Search the standard integration catalog for `YnBlue`.
3. Download `YnBlue`.
4. Restart Home Assistant.
5. Add the integration from `Settings -> Devices & Services`.

### Manual

Copy `custom_components/ynblue` into your Home Assistant `config/custom_components` directory and restart Home Assistant.

## Configuration

The integration uses your YnBlue cloud email address and password.

One Home Assistant config entry represents one YnBlue cloud account and discovers all controllers on that account automatically.

## Documentation

- [Support](SUPPORT.md)
- [Changelog](CHANGELOG.md)
- [Contributing](CONTRIBUTING.md)
- [Troubleshooting guide](docs/troubleshooting.md)
- [Dashboard example](docs/dashboard-setup.md)
- [Product specification](docs/product-specification.md)
- [Technical architecture](docs/technical-architecture.md)
- [Security hardening](docs/security-hardening.md)
- [Release process](docs/release-process.md)
- [Usage metrics and measurement limits](docs/usage-metrics.md)
- [v0.3.2 release notes](docs/release-notes-v0.3.2.md)
- [v0.3.2 technical release review](docs/release-review-v0.3.2.md)
- [Core readiness notes](docs/core-readiness.md)

## Support

- Use the [troubleshooting guide](docs/troubleshooting.md) before opening an issue.
- Open a GitHub issue for confirmed bugs, unsupported controller behavior, or feature requests.
- Include the Home Assistant version, YnBlue integration version, controller model or product name, and redacted logs.
- Do not post passwords, tokens, exact GPS coordinates, or unredacted diagnostics publicly.

## Release And Upgrade Model

- HACS tracks GitHub releases from this repository.
- Each release publishes one `ynblue.zip` package for HACS. Its GitHub download counter measures package requests, including installs, updates, and redownloads; it is not a unique-user counter.
- Stable upgrades should be taken from tagged releases rather than arbitrary commits on `main`.
- Read the [changelog](CHANGELOG.md) and the linked GitHub release notes before upgrading.
- YnBlue 0.3.2 is supported on Home Assistant `2026.6.4` and newer. This minimum is backed by the live 2026.6.4 smoke test and a dedicated CI compatibility lane; 2026.8.1 has a separate regression lane.
