#pragma once
// Experimental mkradio4a CI 0x72 candidate. The two upstream samples carry
// a clear Volume + OMS Date record before a manufacturer-specific tail.
// No AES keys, no authentication, and NO Home Assistant publishing here.
#include "mkradio4a_ci72.h"
#include "xmq_primary_readiness.h"

namespace xmq_standalone {
inline bool decode_mkradio4a_ci72_candidate(
    const std::vector<std::uint8_t> &dll, std::uint32_t expected_inner_id,
    xmq_runtime::XmqFrameResult &out) noexcept {
  out = {};
  Input input{};
  if (!parse_mkradio4a_ci72(dll, expected_inner_id, input) ||
      input.family != Family::Water ||
      input.encoding != xmq_runtime::ApplicationEncoding::StandardDv ||
      input.trust != Trust::VerifiedCleartext)
    return false;
  try {
    // This is deliberately separate from the on-device reviewed registry:
    // it does not approve mkradio4a for live sensors or change auto matching.
    static const xmq_runtime::DriverRegistry registry({
        xmq_runtime::load_driver(xmq_runtime::source_by_name("mkradio4a"))});
    return xmq_runtime::decode_primary_candidate(
        registry, input.inner_mvt, input.encoding, input.application,
        "mkradio4a", {"target_m3"}, {"target_date"}, out);
  } catch (...) {
    out = {};
    return false;
  }
}
} // namespace xmq_standalone
