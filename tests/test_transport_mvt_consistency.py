"""Ensure approved clear-form transports match the detect MVT in each .xmq.

This is an independent, generator-free CI check. It does not authorize
unknown security modes or modify the XMQ parser.
"""
import json
from pathlib import Path
import re
import tempfile
import shutil

COMPONENT = Path(__file__).resolve().parents[1] / "components" / "xmq_meter"
MVT = re.compile(r"^\s*mvt\s*=\s*([A-Z]{3}),([0-9a-fA-F]{2}),([0-9a-fA-F]{2})\s*$", re.M)


def check_consistency(component):
    component = Path(component)
    profiles = json.loads((component / "validated_profiles.json").read_text(encoding="utf-8"))
    transports = json.loads((component / "transport_signatures.json").read_text(encoding="utf-8"))
    count = 0
    for profile in profiles:
        driver = profile["driver"]
        source = (component / "drivers" / (driver + ".xmq")).read_text(encoding="utf-8")
        actual = {
            (manufacturer, int(version, 16), int(kind, 16))
            for manufacturer, version, kind in MVT.findall(source)
        }
        if not actual:
            raise ValueError("No MVT detection in approved driver: " + driver)
        clear = {
            ("TCH", row["version"], row["type"])
            for row in transports
            if row["driver"] == driver and row["security"] == "clear_form"
        }
        if actual != clear:
            raise ValueError("Clear-form transport/MVT mismatch for " + driver
                             + ": driver=" + repr(sorted(actual))
                             + " transport=" + repr(sorted(clear)))
        count += len(clear)
    return count


if __name__ == "__main__":
    assert check_consistency(COMPONENT) == 6
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        shutil.copytree(COMPONENT / "drivers", root / "drivers")
        shutil.copy2(COMPONENT / "validated_profiles.json", root / "validated_profiles.json")
        records = json.loads((COMPONENT / "transport_signatures.json").read_text())
        # Both a missing MVT and an invented MVT must fail the check.
        changes = [
            [r for r in records if not (r["driver"] == "mkradio4" and r["version"] == 112 and r["type"] == 114)],
            records + [dict(records[0], version=0x01)],
        ]
        for case in changes:
            (root / "transport_signatures.json").write_text(json.dumps(case), encoding="utf-8")
            try:
                check_consistency(root)
            except ValueError as error:
                assert "mismatch" in str(error), str(error)
            else:
                raise AssertionError("MVT drift accepted")
    print("XMQ_CLEAR_TRANSPORT_MVT_CONSISTENCY_OK")
