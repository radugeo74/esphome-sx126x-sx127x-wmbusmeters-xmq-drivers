"""Regression checks: YAML driver/family compatibility, including future manifests."""
import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1] / "components" / "xmq_meter"
spec = importlib.util.spec_from_file_location("profile_validation", ROOT / "profile_validation.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

families = mod.approved_families(ROOT)
assert families == {"fhkvdataiii": "heat", "mkradio4": "water"}
for family, driver in (("heat", "auto"), ("water", "auto"),
                       ("heat", "fhkvdataiii"), ("water", "mkradio4"),
                       ("water", "mkradio4a")):
    conf = {"family": family, "driver": driver}
    assert mod.validate_driver_family(conf, families) is conf

for family, driver in (("heat", "mkradio4"), ("water", "fhkvdataiii"),
                       ("heat", "mkradio4a"), ("water", "unapproved")):
    try:
        mod.validate_driver_family({"family": family, "driver": driver}, families)
    except ValueError:
        pass
    else:
        raise AssertionError("Invalid XMQ family/driver accepted: " + family + "/" + driver)

with TemporaryDirectory() as temp:
    manifest = Path(temp) / "validated_profiles.json"
    manifest.write_text(json.dumps([
        {"driver": "synthetic", "family": "water", "required_numeric": ["target_m3"]},
    ]), encoding="utf-8")
    custom = mod.approved_families(temp)
    assert custom == {"synthetic": "water"}
    assert mod.validate_driver_family({"family": "water", "driver": "synthetic"}, custom)
    try:
        mod.validate_driver_family({"family": "heat", "driver": "synthetic"}, custom)
    except ValueError:
        pass
    else:
        raise AssertionError("Synthetic profile family mismatch accepted")
print("XMQ_YAML_PROFILE_VALIDATION_OK")
