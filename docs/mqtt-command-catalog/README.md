# MQTT Command Catalog

This directory contains the current YnBlue MQTT topic inventory as of 2026-08-01.

The catalog documents all MQTT topics that were scanned or reverse-engineered from:

- the Home Assistant integration source code
- the integration test suite
- saved device snapshots
- live broker interaction during pH calibration work on 2026-08-01

This is a catalog of all known or scanned topics. It is not proof that no additional private YnBlue topics exist upstream.

## Files

- `catalog.json`: machine-readable topic inventory with payload examples, confidence levels, and source references

## Confidence Levels

- `confirmed_in_source`: topic is explicitly present in the integration source code
- `confirmed_live`: topic was used successfully against the live YnBlue broker
- `parser_supported`: the integration parser accepts this topic family, but the exact live topic variants may still be broader
- `inferred_from_entities`: the generic hub method is confirmed in source, and the concrete section names come from entity mappings

## Broker Profile

- Host: `mqtt.yneom-iot.com`
- Port: `443`
- Transport: `websockets`
- WebSocket path: `/mqtt`
- MQTT username: `JWT-client`
- Protocol: `MQTTv311`
- TLS: enabled

## Current Findings

- The integration uses short-lived MQTT sessions for both snapshot reads and command writes.
- Full snapshot requests use `/YnBlue/{device_id}/json/all` and wait for `/YnBlue/{device_id}/data/json/all`.
- The runtime parser also accepts `/YnBlue/{device_id}/data/json/measured` and generic `/YnBlue/{device_id}/data/json/{section_path}` updates.
- A live pH calibration topic exists at `/YnBlue/{device_id}/pH/calibration`, but it is not yet wired into the Home Assistant integration.
- No separate pH sensor reinitialization or reset topic was found during this scan.

## Main Topic Families

- Snapshot request and response
- Controller status acknowledgements
- System commands
- Mode and target commands
- Port state commands
- RGB program command
- Consumption reset commands
- Live-only pH calibration command

## Recommended Next Step

If we want to go beyond the currently integrated surface, the next useful step is to add a controlled reverse-engineering harness that can subscribe to live MQTT updates and persist unknown topic families into a dedicated capture log.
