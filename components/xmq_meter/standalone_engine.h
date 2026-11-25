#pragma once
// Experimental no-legacy XMQ application processor. NO radio, no wmbus_common,
// no Telegram::parse / handleTelegram, no legacy snapshot and no HA writer.
// The independent transport/security adaptor must establish trusted plaintext.
#include "xmq_primary_readiness.h"
#include "xmq_driver_sources.h"
#include <cstdint>
#include <string>
#include <vector>

namespace xmq_standalone {
enum class Family : std::uint8_t { Heat, Water };
enum class Trust : std::uint8_t { Unknown, Ciphertext, VerifiedCleartext };
struct Input {
  Family family;
  xmq_runtime::Mvt inner_mvt;
  xmq_runtime::ApplicationEncoding encoding;
  std::vector<std::uint8_t> application;
  Trust trust{Trust::Unknown};
};
// Only reviewed end-to-end profiles are eligible for publication.
// The catalog can contain additional XMQ files without activating them.
inline const xmq_runtime::DriverRegistry &validated_registry() {
  static const xmq_runtime::DriverRegistry registry({
      xmq_runtime::load_driver(xmq_runtime::source_by_name("fhkvdataiii")),
      xmq_runtime::load_driver(xmq_runtime::source_by_name("mkradio4"))});
  return registry;
}

inline bool decode(const Input &input, xmq_runtime::XmqFrameResult &out,
                   const std::string &explicit_driver = "auto") noexcept {
  out = {};
  if (input.trust != Trust::VerifiedCleartext) return false;
  if (explicit_driver != "auto" && explicit_driver != "fhkvdataiii" &&
      explicit_driver != "mkradio4") return false;
  try {
    // Auto selects on the inner MVT, not on family defaults.
    // Zero or multiple matching drivers fail closed in DriverRegistry::select.
    const auto &registry = validated_registry();
    const auto &selected = registry.select(
        input.inner_mvt, explicit_driver == "auto" ? "" : explicit_driver);
    if (selected.name == "fhkvdataiii" && input.family == Family::Heat)
      return xmq_runtime::decode_primary_candidate(
          registry, input.inner_mvt, input.encoding, input.application,
          selected.name,
          {"current_hca", "previous_hca", "temp_room_c", "temp_radiator_c"},
          {}, out);
    if (selected.name == "mkradio4" && input.family == Family::Water)
      return xmq_runtime::decode_primary_candidate(
          registry, input.inner_mvt, input.encoding, input.application,
          selected.name, {"target_m3", "total_m3"}, {}, out);
  } catch (...) {
    out = {};
  }
  return false;
}
} // namespace xmq_standalone
