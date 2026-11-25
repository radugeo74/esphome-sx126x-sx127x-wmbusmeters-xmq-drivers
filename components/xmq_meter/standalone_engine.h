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
// The generated registry includes only reviewed profiles from the manifest.
inline const xmq_runtime::DriverRegistry &validated_registry() {
  static const xmq_runtime::DriverRegistry registry([] {
    std::size_t count = 0;
    const auto *profiles = xmq_runtime::validated_profile_catalog(count);
    std::vector<xmq_runtime::Driver> drivers;
    drivers.reserve(count);
    for (std::size_t i = 0; i < count; ++i) {
      const auto *source = xmq_runtime::source_by_name(profiles[i].name);
      if (source == nullptr) throw xmq_runtime::DriverSelectionError("approved driver missing");
      drivers.push_back(xmq_runtime::load_driver(source));
    }
    return drivers;
  }());
  return registry;
}

inline bool decode(const Input &input, xmq_runtime::XmqFrameResult &out,
                   const std::string &explicit_driver = "auto") noexcept {
  out = {};
  if (input.trust != Trust::VerifiedCleartext ||
      (input.family != Family::Heat && input.family != Family::Water))
    return false;
  try {
    const auto &registry = validated_registry();
    const auto &selected = registry.select(
        input.inner_mvt, explicit_driver == "auto" ? "" : explicit_driver);
    std::size_t count = 0;
    const auto *profiles = xmq_runtime::validated_profile_catalog(count);
    for (std::size_t i = 0; i < count; ++i) {
      const auto &profile = profiles[i];
      if (selected.name != profile.name) continue;
      if ((input.family == Family::Heat) != (std::string(profile.family) == "heat"))
        return false;
      std::vector<std::string> required;
      const std::string fields(profile.required_numeric);
      std::size_t pos = 0;
      while (pos < fields.size()) {
        const auto end = fields.find(',', pos);
        required.push_back(fields.substr(pos, end == std::string::npos ? end : end - pos));
        if (end == std::string::npos) break;
        pos = end + 1;
      }
      return xmq_runtime::decode_primary_candidate(
          registry, input.inner_mvt, input.encoding, input.application,
          selected.name, required, {}, out);
    }
  } catch (...) {
    out = {};
  }
  return false;
}
} // namespace xmq_standalone
