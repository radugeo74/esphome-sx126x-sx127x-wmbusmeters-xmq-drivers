#pragma once
// Experimental input boundary for future encrypted WMBus application payloads.
// There is intentionally NO decryptor registered here. A correctly shaped
// ciphertext/key/IV is not proof of successful decryption or authenticity.
// In particular, never promote ciphertext to VerifiedCleartext.
#include "standalone_engine.h"
#include <array>
#include <cstddef>
#include <cstdint>
#include <vector>

namespace xmq_security {
struct EncryptedFrame {
  std::array<std::uint8_t, 16> key{};
  std::array<std::uint8_t, 16> iv{};
  std::vector<std::uint8_t> ciphertext;
  xmq_standalone::Family family{xmq_standalone::Family::Water};
  xmq_runtime::Mvt inner_mvt;
};

inline bool valid_aes128_cbc_shape(const EncryptedFrame &frame) noexcept {
  return !frame.ciphertext.empty() && frame.ciphertext.size() <= 1024 &&
         frame.ciphertext.size() % 16 == 0;
}

// ALWAYS fails closed until a reviewed decryptor, integrity verification,
// meter-key binding, and anti-replay handling are explicitly implemented.
// Keep output blank even if the caller has supplied a valid-looking frame.
inline bool decode_encrypted_pending(const EncryptedFrame &,
                                     xmq_runtime::XmqFrameResult &out) noexcept {
  out = {};
  return false;
}
} // namespace xmq_security
