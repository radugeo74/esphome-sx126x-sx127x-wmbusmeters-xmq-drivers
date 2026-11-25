"""Pending encrypted transport entries must never become publishable."""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory

component = Path(__file__).resolve().parents[1] / "components" / "xmq_meter"
spec = importlib.util.spec_from_file_location("gen", component / "generate_drivers.py")
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)

with TemporaryDirectory() as d:
    root = Path(d)
    shutil.copytree(component / "drivers", root / "drivers")
    shutil.copy2(component / "validated_profiles.json", root / "validated_profiles.json")
    signatures = json.loads((component / "transport_signatures.json").read_text())
    signatures[0]["security"] = "encrypted_pending"
    (root / "transport_signatures.json").write_text(json.dumps(signatures))
    gen.generate_driver_header(root)
    test = root / "pending.cpp"
    test.write_text(r'''
#include "xmq_driver_sources.h"
#include <cassert>
int main() {
  std::size_t n = 0;
  auto catalog = xmq_runtime::transport_signature_catalog(n);
  assert(n == 14 && catalog[0].security_mode == 1);
  unsigned char sample[] = {0x11};
  // The 0x69/0x80/A0/0x11 entry is pending: must not be accepted.
  assert(xmq_runtime::match_transport_signature(
      0x69, 0x80, 0xA0, sample, sizeof(sample)) == nullptr);
  unsigned char other[] = {0x0f};
  assert(xmq_runtime::match_transport_signature(
      0x69, 0x80, 0xA0, other, sizeof(other)) != nullptr);
  return 0;
}
''')
    output = root / "pending"
    subprocess.run(["g++", "-std=c++17", "-Wall", "-Wextra", "-Werror",
                    "-pedantic", "-I" + str(root), str(test), "-o", str(output)],
                   check=True)
    subprocess.run([str(output)], check=True)
    signatures[0]["security"] = "unknown_mode"
    (root / "transport_signatures.json").write_text(json.dumps(signatures))
    try:
        gen.generate_driver_header(root)
    except ValueError as e:
        assert "security mode" in str(e)
    else:
        raise AssertionError("Unknown security mode was compiled")
print("XMQ_ENCRYPTED_PENDING_FAIL_CLOSED_OK")
