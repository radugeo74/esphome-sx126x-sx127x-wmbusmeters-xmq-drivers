#pragma once
// CI 0x72 full-frame adapter for the reviewed mkradio4a upstream examples.
// This prepares data only; it does not authenticate data, decrypt the tail,
// register a new driver or publish sensors. Usable in host tests and ESPHome.
#include "standalone_engine.h"
#include <cstddef>
#include <cstdint>
#include <vector>

namespace xmq_standalone {
inline bool parse_mkradio4a_ci72(const std::vector<std::uint8_t> &dll,
                                 std::uint32_t expected_inner_id,
                                 Input &input) noexcept {
  // Both upstream examples have a distinct OUTER Techem DLL identity and
  // INNER meter ID. Never bind to outer ID for CI 0x72.
  input = {Family::Water, {}, xmq_runtime::ApplicationEncoding::StandardDv,
           {}, Trust::Unknown};
  if (dll.size() < 35 || dll.size() > 256 ||
      dll.size() != static_cast<std::size_t>(dll[0]) + 1 ||
      dll[1] != 0x44 || dll[2] != 0x68 || dll[3] != 0x50 ||
      dll[8] != 0x95 || dll[9] != 0x37 || dll[10] != 0x72)
    return false;
  // Serial is packed BCD (e.g. 25 38 95 66 -> 0x66953825),
  // matching the component's existing hexadecimal meter_id contract.
  std::uint32_t inner_id = 0;
  for (unsigned i=0; i<4; ++i) {
    const std::uint8_t byte = dll[11 + i];
    if ((byte & 0x0f) > 9 || (byte >> 4) > 9) return false;
    inner_id |= std::uint32_t(byte) << (8*i);
  }
  if (inner_id != expected_inner_id) return false;
  // The two published upstream examples have the same TPL configuration.
  // Preserve their manufacturer-specific encrypted tail as *untrusted*:
  // only the clear DIF/VIF prefix ahead of 0F may be decoded.
  if (dll[20] != 0x00 || dll[21] != 0x30 || dll[22] != 0x05 ||
      dll[23] != 0x2f || dll[24] != 0x2f ||
      dll[25] != 0x43 || dll[26] != 0x15 ||
      dll[30] != 0x42 || dll[31] != 0x6c ||
      dll[34] != 0x0f)
    return false;
  // The original .xmq supports the outer TCH/95/37 MVT on both examples.
  // Do not assume the inner manufacturer has the same MVT.
  input.inner_mvt = {"TCH", 0x95, 0x37};
  input.application.assign(dll.begin() + 25, dll.begin() + 35);
  input.trust = Trust::VerifiedCleartext;
  return true;
}
} // namespace xmq_standalone
