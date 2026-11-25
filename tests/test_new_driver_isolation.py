"""New driver must be discovered without becoming eligible to publish.

Uses a temporary copy, never changes real drivers, YAML, or firmware.
"""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "components" / "xmq_meter"

spec = importlib.util.spec_from_file_location("xmq_generate_drivers", COMPONENT / "generate_drivers.py")
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)

with TemporaryDirectory() as directory:
    temp = Path(directory)
    shutil.copytree(COMPONENT / "drivers", temp / "drivers")
    shutil.copy2(COMPONENT / "validated_profiles.json", temp / "validated_profiles.json")
    shutil.copy2(COMPONENT / "standalone_engine.h", temp / "standalone_engine.h")

    before = gen.generate_driver_header(temp).read_text(encoding="utf-8")
    new_driver = temp / "drivers" / "synthetic_meter.xmq"
    new_driver.write_text(
        "driver {\\n"
        "  name = synthetic_meter\\n"
        "  meter_type = WaterMeter\\n"
        "  manufacturer = Test\\n"
        "  detect { mvt = TST,01,02 }\\n"
        "  fields { field { name = synthetic\\n"
        "                   quantity = Volume } }\\n"
        "}\\n",
        encoding="utf-8",
    )
    after = gen.generate_driver_header(temp).read_text(encoding="utf-8")
    assert after != before
    assert "source_synthetic_meter()" not in before
    assert "source_synthetic_meter()" in after
    assert json.loads((temp / "validated_profiles.json").read_text(encoding="utf-8")) == [
        {"driver": "fhkvdataiii", "family": "heat", "required_numeric": [
            "current_hca", "previous_hca", "temp_room_c", "temp_radiator_c"]},
        {"driver": "mkradio4", "family": "water", "required_numeric": ["target_m3", "total_m3"]},
    ]

    test_cpp = temp / "new_driver_test.cpp"
    test_cpp.write_text(r'''
#include "standalone_engine.h"
#include <cassert>
#include <iostream>

int main() {
  std::size_t all_count = 0;
  auto all = xmq_runtime::driver_catalog(all_count);
  assert(all_count == 4);
  assert(xmq_runtime::source_by_name("synthetic_meter") != nullptr);
  std::size_t approved_count = 0;
  auto approved = xmq_runtime::validated_profile_catalog(approved_count);
  assert(approved_count == 2);
  for (std::size_t i = 0; i < approved_count; ++i)
    assert(std::string(approved[i].name) != "synthetic_meter");

  xmq_runtime::DriverRegistry all_registry({
      xmq_runtime::load_driver(xmq_runtime::source_by_name("synthetic_meter"))});
  assert(all_registry.select({"TST", 0x01, 0x02}).name == "synthetic_meter");

  bool unapproved_rejected = false;
  try {
    (void)xmq_standalone::validated_registry().select({"TST", 0x01, 0x02});
  } catch (const xmq_runtime::DriverSelectionError &) {
    unapproved_rejected = true;
  }
  assert(unapproved_rejected);

  xmq_standalone::Input input{
      xmq_standalone::Family::Water, {"TST", 0x01, 0x02},
      xmq_runtime::ApplicationEncoding::StandardDv, {0x00},
      xmq_standalone::Trust::VerifiedCleartext};
  xmq_runtime::XmqFrameResult out;
  assert(!xmq_standalone::decode(input, out, "auto"));
  assert(out.numeric.empty() && out.dates.empty());
  assert(!xmq_standalone::decode(input, out, "synthetic_meter"));
  assert(out.numeric.empty() && out.dates.empty());
  std::cout << "XMQ_UNAPPROVED_DRIVER_FAIL_CLOSED_OK" << '\\n';
}
''', encoding="utf-8")
    executable = temp / "new_driver_test"
    subprocess.run(
        ["g++", "-std=c++17", "-O1", "-Wall", "-Wextra", "-Werror",
         "-pedantic", "-I" + str(temp), "-I" + str(COMPONENT),
         str(test_cpp), "-o", str(executable)],
        check=True,
    )
    subprocess.run([str(executable)], check=True)
    # Invalid filenames and mismatched names must fail generation.
    new_driver.write_text("driver { name = different }\\n", encoding="utf-8")
    try:
        gen.generate_driver_header(temp)
    except ValueError as exc:
        assert "name mismatch" in str(exc)
    else:
        raise AssertionError("Mismatched new driver name was accepted")

print("XMQ_NEW_DRIVER_ISOLATION_OK")
