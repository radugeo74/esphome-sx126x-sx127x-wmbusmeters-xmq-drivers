// HOST-ONLY AES-CMAC conformance probe: RFC 4493 section 4.
// This verifies the OpenSSL 3 primitive, NOT any OMS WMBus telegram policy.
// No production key, meter ID, firmware linkage or publication authorization.
#include "encrypted_input_gate.h"
#include <openssl/evp.h>
#include <openssl/core_names.h>
#include <openssl/crypto.h>
#include <array>
#include <cassert>
#include <cstddef>
#include <cstdint>
#include <iostream>
#include <memory>
#include <string>
#include <vector>

using Bytes = std::vector<std::uint8_t>;
using Tag = std::array<std::uint8_t, 16>;
static Bytes hex(const std::string &s) {
  assert(s.size() % 2 == 0);
  Bytes out;
  out.reserve(s.size() / 2);
  for (std::size_t i = 0; i < s.size(); i += 2)
    out.push_back(static_cast<std::uint8_t>(std::stoul(s.substr(i,2), nullptr, 16)));
  return out;
}
static bool cmac_rfc4493(const Bytes &key, const Bytes &msg, Tag &tag) {
  tag.fill(0);
  if (key.size() != 16) return false;
  std::unique_ptr<EVP_MAC, decltype(&EVP_MAC_free)>
      mac(EVP_MAC_fetch(nullptr, "CMAC", nullptr), EVP_MAC_free);
  if (!mac) return false;
  std::unique_ptr<EVP_MAC_CTX, decltype(&EVP_MAC_CTX_free)>
      ctx(EVP_MAC_CTX_new(mac.get()), EVP_MAC_CTX_free);
  if (!ctx) return false;
  char cipher[] = "AES-128-CBC";
  OSSL_PARAM params[] = {
      OSSL_PARAM_construct_utf8_string(OSSL_MAC_PARAM_CIPHER, cipher, 0),
      OSSL_PARAM_construct_end()
  };
  std::size_t out_len = 0;
  if (EVP_MAC_init(ctx.get(), key.data(), key.size(), params) != 1 ||
      (!msg.empty() && EVP_MAC_update(ctx.get(), msg.data(), msg.size()) != 1) ||
      EVP_MAC_final(ctx.get(), tag.data(), &out_len, tag.size()) != 1 ||
      out_len != tag.size()) {
    tag.fill(0);
    return false;
  }
  return true;
}
int main() {
  const Bytes key = hex("2b7e151628aed2a6abf7158809cf4f3c");
  const Bytes full = hex(
      "6bc1bee22e409f96e93d7e117393172a"
      "ae2d8a571e03ac9c9eb76fac45af8e51"
      "30c81c46a35ce411e5fbc1191a0a52ef"
      "f69f2445df4f9b17ad2b417be66c3710");
  const struct { std::size_t length; const char *expected; } examples[] = {
      {0,  "bb1d6929e95937287fa37d129b756746"},
      {16, "070a16b46b4d4144f79bdd9dd04a287c"},
      {40, "dfa66747de9ae63030ca32611497c827"},
      {64, "51f0bebf7e3b9d92fc49741779363cfe"},
  };
  for (const auto &example : examples) {
    Tag computed{};
    const Bytes message(full.begin(), full.begin() + example.length);
    assert(cmac_rfc4493(key, message, computed));
    const Bytes expected = hex(example.expected);
    assert(CRYPTO_memcmp(computed.data(), expected.data(), computed.size()) == 0);
  }
  Tag original{}, changed{};
  const Bytes first(full.begin(), full.begin() + 16);
  assert(cmac_rfc4493(key, first, original));
  Bytes modified = first;
  modified[0] ^= 0x01;
  assert(cmac_rfc4493(key, modified, changed));
  assert(CRYPTO_memcmp(original.data(), changed.data(), original.size()) != 0);
  assert(!cmac_rfc4493(Bytes(15, 0), first, changed));
  assert(changed == Tag{});
  xmq_security::EncryptedFrame frame;
  frame.inner_mvt = {"TCH", 0x95, 0x62};
  frame.ciphertext.assign(16, 0x11);
  xmq_runtime::XmqFrameResult output;
  output.driver = "stale";
  assert(!xmq_security::decode_encrypted_pending(frame, output));
  assert(output.driver.empty() && output.numeric.empty() && output.dates.empty());
  std::cout << "XMQ_RFC4493_AES_CMAC_HOST_ONLY_NO_PUBLISH_OK\n";
}
