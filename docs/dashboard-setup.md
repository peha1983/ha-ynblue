# Dashboard Setup Example

This document provides a simple Lovelace layout that works well with the YnBlue entity model.

Adjust entity IDs to match your Home Assistant instance.

## Suggested card structure

- Overview card for water quality and freshness
- Equipment card for lights, robot, swim jet, and relays
- Setpoints card for pH, treatment, and heater targets
- Diagnostics card for online state and last cloud contact

## Example YAML

```yaml
type: vertical-stack
cards:
  - type: entities
    title: Pool Overview
    entities:
      - entity: sensor.pool_water_temperature
      - entity: sensor.pool_ph_measured
      - entity: sensor.pool_chemical_measured
      - entity: sensor.pool_ph_tank_level
      - entity: sensor.pool_chemical_tank_level
      - entity: sensor.pool_live_data_age_minutes
      - entity: binary_sensor.pool_online
      - entity: sensor.pool_last_cloud_contact

  - type: entities
    title: Equipment
    show_header_toggle: false
    entities:
      - entity: light.pool_light
      - entity: light.pool_rgb_light
      - entity: switch.pool_robot
      - entity: switch.pool_swim_jet
      - entity: switch.pool_fountain
      - entity: switch.pool_aux_switch

  - type: entities
    title: Setpoints And Modes
    entities:
      - entity: number.pool_ph_target
      - entity: number.pool_chemical_target
      - entity: number.pool_heater_target
      - entity: select.pool_filter_mode
      - entity: select.pool_heater_mode
      - entity: select.pool_chemical_mode
      - entity: select.pool_ph_mode

  - type: entities
    title: Actions
    entities:
      - entity: button.pool_request_snapshot
      - entity: button.pool_force_measurement
      - entity: button.pool_inject_ph
      - entity: button.pool_stop_ph_injection
      - entity: button.pool_restart_controller

  - type: history-graph
    title: Water Trend
    hours_to_show: 24
    entities:
      - entity: sensor.pool_water_temperature
      - entity: sensor.pool_ph_measured
      - entity: sensor.pool_chemical_measured
```

## Recommended UI conventions

- Show `live_data_age_minutes` near the primary measurements so stale data is obvious.
- Keep `online` and `last_cloud_contact` visible on the main dashboard.
- Put restart and injection actions in a dedicated card, not beside everyday toggles.
- Separate diagnostics from everyday controls if multiple family members use the dashboard.
