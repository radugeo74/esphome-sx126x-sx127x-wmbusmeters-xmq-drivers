#pragma once
// Shared fail-closed binding: used by both production ESPHome and host tests.
// A recognized clear-form transport signature alone is NOT authentication.
#include "standalone_engine.h"
#include <string>

namespace xmq_standalone {
inline bool decode_transport_bound(const char *transport_driver,
                                   const Input &input,
                                   const std::string &configured_driver,
                                   xmq_runtime::XmqFrameResult &out) noexcept {
  out = {};
  // Approved proprietary TCH A0/A2 clear-form signatures correspond
  // exclusively to original IXML application bytes, not standard DV records.
  if (input.encoding != xmq_runtime::ApplicationEncoding::OriginalIxml ||
      transport_driver == nullptr || transport_driver[0] == '\0' ||
      (configured_driver != "auto" && configured_driver != transport_driver))
    return false;
  if (!decode(input, out, transport_driver) || out.driver != transport_driver) {
    out = {};
    return false;
  }
  return true;
}
} // namespace xmq_standalone
