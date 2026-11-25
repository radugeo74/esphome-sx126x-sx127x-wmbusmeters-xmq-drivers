"""A validated XMQ driver must have at least one reviewed clear-form transport.

A declared driver with no live admitted transport would create misleading YAML
availability, and allowing only pending encrypted signatures must not activate
it. Work entirely in temporary driver/profile/transport copies.
"""
import importlib.util
import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1] / "components" / "xmq_meter"
spec = importlib.util.spec_from_file_location("xmq_generator", ROOT / "generate_drivers.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

signatures = json.loads((ROOT / "transport_signatures.json").read_text(encoding="utf-8"))
profiles = json.loads((ROOT / "validated_profiles.json").read_text(encoding="utf-8"))
approved = {p["driver"] for p in profiles}
clear = {p["driver"] for p in signatures if p["security"] == "clear_form"}
assert clear == approved == {"fhkvdataiii", "mkradio4"}


def verify(changes, expected_error=None):
    with TemporaryDirectory() as temp:
        base = Path(temp)
        shutil.copytree(ROOT / "drivers", base / "drivers")
        shutil.copy2(ROOT / "validated_profiles.json", base / "validated_profiles.json")
        (base / "transport_signatures.json").write_text(
            json.dumps(changes), encoding="utf-8"
        )
        if expected_error is None:
            module.generate_driver_header(base)
            return
        try:
            module.generate_driver_header(base)
        except ValueError as exc:
            assert expected_error in str(exc), str(exc)
        else:
            raise AssertionError("Unsafe validated transport profile accepted")


verify(signatures)
# Every signature for heat becomes pending: the driver must no longer be
# advertised as publishable despite remaining in validated_profiles.json.
no_heat = [
    dict(row, security="encrypted_pending") if row["driver"] == "fhkvdataiii" else row
    for row in signatures
]
verify(no_heat, "without clear-form transport: fhkvdataiii")
# Empty clear-form coverage across every driver must be rejected.
all_pending = [dict(row, security="encrypted_pending") for row in signatures]
verify(all_pending, "without clear-form transport")
# Removing a driver's signatures is also rejected.
verify([row for row in signatures if row["driver"] != "mkradio4"],
       "without clear-form transport: mkradio4")
# A single heat signature remains enough to retain the existing approval.
one_heat = [
    row for row in signatures
    if row["driver"] != "fhkvdataiii" or row == next(
        p for p in signatures if p["driver"] == "fhkvdataiii"
    )
]
verify(one_heat)
print("XMQ_VALIDATED_DRIVER_REQUIRES_CLEAR_TRANSPORT_OK")
