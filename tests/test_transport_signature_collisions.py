"""Reject ambiguous proprietary transport signatures before firmware build."""
import importlib.util
import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory

COMPONENT = Path(__file__).resolve().parents[1] / "components" / "xmq_meter"
spec = importlib.util.spec_from_file_location("xmq_driver_generator", COMPONENT / "generate_drivers.py")
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)
original = json.loads((COMPONENT / "transport_signatures.json").read_text(encoding="utf-8"))


def check_case(extra, *, expected):
    with TemporaryDirectory() as folder:
        base = Path(folder)
        shutil.copytree(COMPONENT / "drivers", base / "drivers")
        shutil.copy2(COMPONENT / "validated_profiles.json", base / "validated_profiles.json")
        (base / "transport_signatures.json").write_text(
            json.dumps(original + [extra]), encoding="utf-8"
        )
        if expected == "valid":
            gen.generate_driver_header(base)
            return
        try:
            gen.generate_driver_header(base)
        except ValueError as exc:
            assert expected in str(exc), str(exc)
        else:
            raise AssertionError("Ambiguous signature accepted: " + str(extra))


# Exact duplicate of a currently approved clear-form signature.
check_case(dict(original[0]), expected="Overlapping")
# Same bytes, but a pending encrypted signature must not be shadowed by clear.
check_case(dict(original[0], security="encrypted_pending"), expected="Overlapping")
# Shorter prefix shadows both existing approved water prefixes for this MVT.
water = next(x for x in original if x["driver"] == "mkradio4")
check_case(dict(water, prefix=[6], security="encrypted_pending"), expected="Overlapping")
# Longer prefix may match all the same traffic as an existing shorter entry.
check_case(dict(water, prefix=water["prefix"] + [123]), expected="Overlapping")
# Different driver but colliding version, type, CI and prefix is prohibited.
check_case(dict(water, driver="fhkvdataiii"), expected="Overlapping")
# Non-overlapping prefix with same MVT is safe to describe, but still requires
# reviewed security and driver approval before any publishing can occur.
check_case(dict(water, prefix=[7], security="encrypted_pending"), expected="valid")
# Legitimate baseline remains unchanged and compilable.
with TemporaryDirectory() as folder:
    base = Path(folder)
    shutil.copytree(COMPONENT / "drivers", base / "drivers")
    shutil.copy2(COMPONENT / "validated_profiles.json", base / "validated_profiles.json")
    shutil.copy2(COMPONENT / "transport_signatures.json", base / "transport_signatures.json")
    gen.generate_driver_header(base)
print("XMQ_TRANSPORT_SIGNATURE_PREFIX_COLLISIONS_REJECTED_OK")
