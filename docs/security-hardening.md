# YnBlue Security Hardening

## Threat Model

The integration stores cloud credentials, communicates with an external vendor cloud, and can trigger physical pool actions.

Primary risks:

- leaking credentials or tokens
- over-broad diagnostics
- command abuse or accidental command storms
- weak validation allowing unsafe payloads
- stale or misleading state after transport failures

## Hardening Requirements

### Secrets

- Never log passwords, JWTs, or raw authorization headers.
- Redact credentials and sensitive device/account fields in diagnostics.

### Network boundaries

- Only talk to the fixed YnBlue API and MQTT hosts defined in constants.
- Use TLS with default certificate validation.
- Never disable TLS verification.

### Commands

- Serialize commands per device.
- Validate all numeric and enum inputs server-side before publishing.
- Reject commands when the controller is offline.
- Limit post-command retries and fail closed on timeout.

### Diagnostics and privacy

- Redact registration strings, device identifiers, location data, Wi-Fi SSIDs, serial numbers, and cloud credentials.
- Expose only the minimum useful runtime health metadata.
- Use non-identifying controller ordinals in runtime logs and diagnostic mapping keys.
- Do not copy vendor response bodies, MQTT topics, or raw controller identifiers into warning/error text.

### Operational safety

- Keep physical action helpers explicit and typed.
- Avoid hidden optimistic writes for commands that affect real equipment.
- Require a follow-up sync before reporting success where confirmation is possible.

## Maintenance Guidance

- Treat every new cloud field as untrusted input.
- Add tests for every new command path and every recovery rule.
- Keep the integration honest about its transport behavior and `iot_class`.
