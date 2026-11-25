"""Fail-closed validation for explicitly selected XMQ meter profiles.

Separate from ESPHome imports so it can be tested independently in CI.
"""
import json
from pathlib import Path


def approved_families(component_dir):
    profiles = json.loads((Path(component_dir) / "validated_profiles.json").read_text(encoding="utf-8"))
    if not isinstance(profiles, list) or not profiles:
        raise ValueError("Empty or invalid validated XMQ profiles")
    families = {}
    for item in profiles:
        if not isinstance(item, dict) or set(item) != {"driver", "family", "required_numeric"}:
            raise ValueError("Malformed validated XMQ profile")
        name, family = item["driver"], item["family"]
        if not isinstance(name, str) or not name or name in families or family not in ("heat", "water"):
            raise ValueError("Duplicate/invalid validated XMQ driver")
        families[name] = family
    return families


def validate_driver_family(config, families):
    family = config["family"]
    driver = config.get("driver", "auto")
    if family not in ("heat", "water"):
        raise ValueError("Invalid XMQ meter family")
    if driver == "auto":
        return config
    # Explicit, experimental CI72 candidate only. This is intentionally NOT
    # part of the manifest-approved auto driver registry.
    if driver == "mkradio4a":
        if family != "water":
            raise ValueError("mkradio4a requires water family")
        return config
    if driver not in families:
        raise ValueError("Driver is not in the reviewed XMQ profiles")
    if families[driver] != family:
        raise ValueError("XMQ driver/family mismatch: " + driver + " requires " + families[driver])
    return config
