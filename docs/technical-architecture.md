# YnBlue Technical Architecture

## Runtime Model

Each config entry owns three runtime objects:

- `YnBlueApiClient`: cloud authentication and REST access
- `YnBlueCoordinator`: in-memory device state
- `YnBlueHub`: polling, recovery, command execution, and snapshot orchestration

## Data Sources

### REST metadata

REST metadata provides:

- device identity
- capabilities
- cloud connectivity flags such as `isConnected`
- `date_mqtt_connection`

REST metadata is authoritative for online/offline detection.

### MQTT snapshot

Full state snapshots are fetched over short-lived MQTT WebSocket sessions.

Snapshot data provides:

- measured temperature
- pH
- chemical/ORP values
- tank levels
- output states
- heater/filter/electrolyser runtime sections

Snapshot data is authoritative for detailed telemetry.

## Update Flows

### Startup

1. Validate cloud access and load metadata.
2. Start background metadata refresh.
3. Attempt an initial snapshot for every online controller.
4. Restore the last good Home Assistant state for entities with no fresh snapshot yet.

### Online steady state

1. Metadata refresh runs every 30 seconds.
2. Snapshot refresh runs every 90 seconds for online devices.
3. If metadata indicates a device came back online or reconnected, schedule an immediate snapshot.

### Offline state

1. Metadata refresh continues.
2. Snapshot failures do not discard the last good state.
3. Commands fail fast with a clear offline error.

## Command Model

Every device has a command lock.

Command execution steps:

1. Validate the input against server-side bounds.
2. Reject if the controller is offline.
3. Publish the command over a short-lived MQTT command session.
4. Wait a short settle delay when needed.
5. Fetch one follow-up snapshot and confirm the expected state when confirmation is possible.

## Recovery Strategy

- The integration never trusts a single stale Home Assistant restore state if the recorder contains a newer valid state.
- Metadata refresh is the trigger for automatic recovery after controller reboots.
- Snapshot refresh is idempotent and safe to repeat.

## Maintainability Rules

- One responsibility per helper method.
- No dead transport paths left half-wired in production code.
- Transport concerns stay in the hub.
- Entity classes remain thin state adapters.
