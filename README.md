# YnBlue for Home Assistant

![Validate](https://github.com/peha1983/ha-ynblue/actions/workflows/validate.yml/badge.svg)
![GitHub Release](https://img.shields.io/github/v/release/peha1983/ha-ynblue?display_name=tag&sort=semver)
![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)

`ynblue` is a Home Assistant custom integration for YNEOM/YnBlue pool controllers.

It signs in to the YnBlue cloud, refreshes the JWT automatically, connects to the official YnBlue MQTT WebSocket and exposes live entities in Home Assistant.

## Features

- Water temperature, pH, ORP/treatment, tank levels and Wi-Fi signal
- Online state, filter/heater runtime and sensor fault indicators
- Pool volume, pH target, treatment target and heater target
- Filter, heater, treatment and pH modes
- Light, RGB light, robot and swim jet controls when wired on the controller
- Snapshot, force measurement, pH injection and maintenance/reset buttons

## Installation

### HACS

1. Open HACS.
2. Add `https://github.com/peha1983/ha-ynblue` as a custom repository with type `Integration`.
3. Install `YnBlue`.
4. Restart Home Assistant.
5. Add the integration from `Settings -> Devices & Services`.

### Manual

Copy `custom_components/ynblue` into your Home Assistant `config/custom_components` directory and restart Home Assistant.

## Configuration

The integration uses your YnBlue cloud email address and password.

One Home Assistant config entry represents one YnBlue cloud account and discovers all controllers on that account automatically.

## Notes

- The YnBlue device itself does not expose a local LAN API in the tested setup.
- Live state and control are provided through the official YnBlue cloud MQTT endpoint.
- This integration is designed for Home Assistant `2025.12.x` and newer.
