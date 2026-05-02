"""Helper utilities for the YnBlue integration."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from .const import ENTITY_OBJECT_ID_BY_KEY


def deep_merge_dict(base: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge dictionaries without mutating the inputs."""

    merged = deepcopy(base)
    for key, value in updates.items():
        current = merged.get(key)
        if isinstance(current, dict) and isinstance(value, dict):
            merged[key] = deep_merge_dict(current, value)
        else:
            merged[key] = deepcopy(value)
    return merged


def get_nested_value(data: dict[str, Any] | None, *path: str, default: Any = None) -> Any:
    """Safely fetch a nested value from a dictionary."""

    cursor: Any = data
    for part in path:
        if not isinstance(cursor, dict) or part not in cursor:
            return default
        cursor = cursor[part]
    return cursor


def set_nested_value(path: list[str], value: Any) -> dict[str, Any]:
    """Return a nested dictionary for a given path/value pair."""

    if not path:
        return value
    head, *tail = path
    if not tail:
        return {head: value}
    return {head: set_nested_value(tail, value)}


def copy_device(device: dict[str, Any]) -> dict[str, Any]:
    """Return a detached copy of device data."""

    return deepcopy(device)


def is_port_enabled(device: dict[str, Any], section: str) -> bool:
    """Return whether a port-based functionality is enabled."""

    section_data = device.get(section)
    if not isinstance(section_data, dict):
        return False
    port = section_data.get("port")
    return port is None or port >= 0


def feature_enabled(device: dict[str, Any], feature: str) -> bool:
    """Return whether a functionality flag is enabled."""

    functionalities = device.get("functionalities", {})
    return bool(functionalities.get(feature))


def build_entity_id(unique_id: str, entity_domain: str) -> str | None:
    """Return the canonical English entity_id for a YnBlue unique_id."""

    _, _, key = unique_id.partition("_")
    object_id = ENTITY_OBJECT_ID_BY_KEY.get(key)
    if object_id is None:
        return None
    return f"{entity_domain}.{object_id}"
