# YnBlue Home Assistant Integration Product Specification

## Goal

Provide a production-ready Home Assistant custom integration for YnBlue pool controllers that:

- exposes reliable pool telemetry in Home Assistant
- survives controller offline/online transitions without requiring manual reloads
- confirms or clearly fails user-triggered commands
- remains maintainable by engineers who are not using AI tooling

## Users

- Home Assistant administrators operating a YnBlue-controlled pool
- Maintainers extending or debugging the integration

## Functional Requirements

### Device discovery and authentication

- Authenticate with the YnBlue cloud using email and password.
- Discover every YnBlue controller attached to the configured account.
- Refresh expired JWT tokens automatically.
- Trigger Home Assistant reauthentication when the cloud rejects credentials.

### Telemetry

- Refresh controller metadata on a fixed interval.
- Refresh a full controller snapshot on a fixed interval while the controller is online.
- Trigger an immediate snapshot after the controller comes back online.
- Keep the last good data visible when the controller or cloud is temporarily unavailable.
- Clearly expose controller connectivity and freshness information.

### Recovery behavior

- If the YnBlue controller goes offline, entities must not collapse into a useless wall of unavailable states.
- If the controller comes back online, fresh values must be fetched automatically without reloading the integration.
- If Home Assistant restarts while the controller is offline, the integration must restore the last valid values and reconnect automatically once the controller is back.

### Commands

- Serialize commands per device to avoid race conditions.
- Reject commands when the controller is known offline.
- Re-sync the controller state after every command.
- Fail the Home Assistant service call when a command could not be delivered or the expected post-command state could not be confirmed.

### Diagnostics

- Provide diagnostics that help support without leaking passwords, tokens, or sensitive location/account data.
- Expose health indicators such as online state and last cloud contact.

## Non-Functional Requirements

### Reliability

- Prefer a simpler, field-proven transport strategy over a more complex but unstable one.
- Avoid long-lived runtime paths that are known to reconnect badly with the YnBlue broker.
- Isolate transient transport failures so they do not crash the integration.

### Maintainability

- Keep all source code, variable names, docs, and user-facing labels in English.
- Prefer small helper methods, explicit validation, and typed boundaries over clever abstractions.
- Back every bug fix or runtime rule with automated tests.

### Observability

- Log lifecycle transitions and failures at useful levels.
- Keep logs actionable and free from secrets.

## Product Decisions

### Telemetry strategy

The integration uses:

- periodic REST metadata refresh for connectivity and controller identity
- short-lived MQTT snapshot sessions for reliable state synchronization
- immediate snapshot refresh after important events such as reconnection and commands

This design is chosen because short-lived snapshot sessions were proven reliable in the field, while persistent broker sessions were not consistently stable.

### Freshness semantics

- `binary_sensor.ynblue_online` indicates whether the controller is currently connected to the YnBlue cloud.
- `sensor.ynblue_last_cloud_contact` shows the last known cloud contact timestamp from YnBlue metadata.
- Value entities show the latest confirmed good snapshot, even while the controller is temporarily offline.

## Out of Scope

- Reverse engineering undocumented destructive/chemical workflows beyond safe command support already exposed by the cloud API
- Unsafe live testing of physical actions such as chemical dosing without operator intent
