"""Metadata-only fixtures for protocol research; never load meter keys in CI.

This is not a WMBus decoder or authenticity verifier. It intentionally
cannot authorize publication of an encrypted payload.
"""
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

_HEX = re.compile(r"^[0-9a-fA-F]+$")
_MFCT = re.compile(r"^[A-Z]{3}$")
_ALLOWED = {
    "source", "link_mode", "manufacturer", "version", "device_type",
    "ci", "access_number", "security_configuration_hex", "ciphertext_hex",
    "iv_derivation", "integrity_evidence", "key_reference", "reference_url",
}
_FORBIDDEN = {"key", "aes_key", "secret", "password", "key_hex",
              "plaintext", "decrypted_payload", "private_key"}


def validate_pending_fixture(fixture):
    if not isinstance(fixture, dict) or set(fixture) != _ALLOWED:
        raise ValueError("Missing/unrecognized encrypted fixture metadata")
    if set(fixture) & _FORBIDDEN:
        raise ValueError("Encrypted fixtures must not contain secrets")
    if fixture["source"] not in ("synthetic", "public_reference"):
        raise ValueError("Unsupported fixture source")
    reference = fixture["reference_url"]
    if fixture["source"] == "synthetic":
        if reference is not None:
            raise ValueError("Synthetic fixture must not claim external provenance")
    else:
        if not isinstance(reference, str) or len(reference) > 512:
            raise ValueError("Public fixture needs a documented HTTPS source")
        parts = urlsplit(reference)
        if (parts.scheme != "https" or not parts.hostname or parts.username or
                parts.password or parts.query or parts.fragment or "@" in parts.netloc):
            raise ValueError("Invalid public reference provenance URL")
    if fixture["link_mode"] not in ("T1", "C1"):
        raise ValueError("Unsupported link mode")
    if not isinstance(fixture["manufacturer"], str) or not _MFCT.fullmatch(fixture["manufacturer"]):
        raise ValueError("Manufacturer is not a 3-letter MVT code")
    for name in ("version", "device_type", "ci", "access_number"):
        val = fixture[name]
        if type(val) is not int or not 0 <= val <= 255:
            raise ValueError("Invalid " + name)
    sec = fixture["security_configuration_hex"]
    if not isinstance(sec, str) or len(sec) != 4 or not _HEX.fullmatch(sec):
        raise ValueError("Security configuration must be exactly 2 hex bytes")
    payload = fixture["ciphertext_hex"]
    if not isinstance(payload, str) or len(payload) < 32 or len(payload) > 2048 or len(payload) % 32 or not _HEX.fullmatch(payload):
        raise ValueError("CBC-shaped ciphertext must contain 1..64 AES blocks")
    if fixture["iv_derivation"] != "unknown" and fixture["iv_derivation"] != "documented_not_implemented":
        raise ValueError("No unreviewed IV policy may be assumed")
    if fixture["integrity_evidence"] != "not_verified":
        raise ValueError("No fixture may claim verified authenticity")
    if fixture["key_reference"] != "not_in_repository":
        raise ValueError("Never store keys or key references in fixtures")
    return fixture


def _reject_duplicate_fields(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate encrypted fixture field: " + key)
        result[key] = value
    return result


def load_pending_fixture(path):
    payload = json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_fields)
    return validate_pending_fixture(payload)
