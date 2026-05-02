# YnBlue for Home Assistant

`ynblue` is a Home Assistant custom integration for YNEOM/YnBlue pool controllers.

It logs in to the YnBlue cloud, keeps the JWT fresh, connects to the YnBlue MQTT WebSocket and exposes live Home Assistant entities for:

- Water temperature, pH, ORP/treatment and tank levels
- Online state, filter/heater/electrolyser runtime and sensor fault indicators
- Pool volume, pH target, treatment target and heater target
- Filter, heater, treatment and pH modes
- RGB/light outputs, auxiliary switches, robot and swim jet when wired
- Snapshot, force measurement, pH injection and maintenance/reset actions

## Installation

### HACS

1. Open HACS.
2. Add this repository as a custom repository with type `Integration`.
3. Install `YnBlue`.
4. Restart Home Assistant.
5. Add the integration from `Settings -> Devices & Services`.

### Manual

Copy `custom_components/ynblue` into your Home Assistant `config/custom_components` directory and restart Home Assistant.

## Configuration

The integration uses your YnBlue cloud email and password.

One Home Assistant config entry represents one YnBlue cloud account and discovers all controllers on that account automatically.

## Notes

- The YnBlue device itself does not expose a local LAN API in the tested setup.
- Live state and control are provided through the official YnBlue cloud MQTT endpoint.
- This integration is designed for Home Assistant `2025.12.x` and newer.
