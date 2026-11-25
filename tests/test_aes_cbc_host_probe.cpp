// HOST-ONLY cryptographic primitive test. NOT part of ESPHome firmware.
// Decrypted AES-CBC bytes are unauthenticated and must not be published.
#include "encrypted_input_gate.h"
#include <openssl/evp.h>
#include <array>
#include <cassert>
#include <cstdint>
#include <iostream>
#include <memory>
#include <vector>

using Block = std::array<std::uint8_t, 16>;
struct UnauthenticatedPlaintext {
  std::vector<std::uint8_t> bytes;
};

static bool decrypt_aes128_cbc_untrusted(const Block &key, const Block &iv,
                                        const std::vector<std::uint8_t> &cipher,
                                        UnauthenticatedPlaintext &output) {
  output.bytes.clear();
  xmq_security::EncryptedFrame input;
  input.ciphertext = cipher;
  if (!xmq_security::valid_aes128_cbc_shape(input)) return false;
  std::unique_ptr<EVP_CIPHER_CTX, decltype(&EVP_CIPHER_CTX_free)>
      ctx(EVP_CIPHER_CTX_new(), EVP_CIPHER_CTX_free);
  if (!ctx) return false;
  if (EVP_DecryptInit_ex(ctx.get(), EVP_aes_128_cbc(), nullptr,
                         key.data(), iv.data()) != 1 ||
      EVP_CIPHER_CTX_set_padding(ctx.get(), 0) != 1) return false;
  output.bytes.resize(cipher.size() + 16);
  int written = 0;
  int final_bytes = 0;
  if (EVP_DecryptUpdate(ctx.get(), output.bytes.data(), &written,
                        cipher.data(), static_cast<int>(cipher.size())) != 1 ||
      EVP_DecryptFinal_ex(ctx.get(), output.bytes.data() + written,
                          &final_bytes) != 1) {
    output.bytes.clear();
    return false;
  }
  output.bytes.resize(static_cast<std::size_t>(written + final_bytes));
  return true; // ONLY cryptographic transformation, NOT telegram validation.
}
int main() {
  const Block key{0x2b,0x7e,0x15,0x16,0x28,0xae,0xd2,0xa6,
                  0xab,0xf7,0x15,0x88,0x09,0xcf,0x4f,0x3c};
  const Block iv{0x00,0x01,0x02,0x03,0x04,0x05,0x06,0x07,
                 0x08,0x09,0x0a,0x0b,0x0c,0x0d,0x0e,0x0f};
  const std::vector<std::uint8_t> plaintext{
      0x6b,0xc1,0xbe,0xe2,0x2e,0x40,0x9f,0x96,0xe9,0x3d,0x7e,0x11,0x73,0x93,0x17,0x2a,
      0xae,0x2d,0x8a,0x57,0x1e,0x03,0xac,0x9c,0x9e,0xb7,0x6f,0xac,0x45,0xaf,0x8e,0x51,
      0x30,0xc8,0x1c,0x46,0xa3,0x5c,0xe4,0x11,0xe5,0xfb,0xc1,0x19,0x1a,0x0a,0x52,0xef,
      0xf6,0x9f,0x24,0x45,0xdf,0x4f,0x9b,0x17,0xad,0x2b,0x41,0x7b,0xe6,0x6c,0x37,0x10};
  const std::vector<std::uint8_t> ciphertext{
      0x76,0x49,0xab,0xac,0x81,0x19,0xb2,0x46,0xce,0xe9,0x8e,0x9b,0x12,0xe9,0x19,0x7d,
      0x50,0x86,0xcb,0x9b,0x50,0x72,0x19,0xee,0x95,0xdb,0x11,0x3a,0x91,0x76,0x78,0xb2,
      0x73,0xbe,0xd6,0xb8,0xe3,0xc1,0x74,0x3b,0x71,0x16,0xe6,0x9e,0x22,0x22,0x95,0x16,
      0x3f,0xf1,0xca,0xa1,0x68,0x1f,0xac,0x09,0x12,0x0e,0xca,0x30,0x75,0x86,0xe1,0xa7};
  UnauthenticatedPlaintext untrusted;
  assert(decrypt_aes128_cbc_untrusted(key, iv, ciphertext, untrusted));
  assert(untrusted.bytes == plaintext);
  Block other_iv = iv;
  other_iv[0] ^= 1;
  assert(decrypt_aes128_cbc_untrusted(key, other_iv, ciphertext, untrusted));
  assert(untrusted.bytes[0] == (plaintext[0] ^ 1));
  for (std::size_t i = 1; i < plaintext.size(); ++i) assert(untrusted.bytes[i] == plaintext[i]);
  auto short_cipher = ciphertext;
  short_cipher.pop_back();
  assert(!decrypt_aes128_cbc_untrusted(key, iv, short_cipher, untrusted));
  assert(untrusted.bytes.empty());
  xmq_security::EncryptedFrame incoming;
  incoming.ciphertext = ciphertext;
  incoming.key = key;
  incoming.iv = iv;
  xmq_runtime::XmqFrameResult output;
  output.driver = "stale";
  assert(!xmq_security::decode_encrypted_pending(incoming, output));
  assert(output.driver.empty() && output.numeric.empty() && output.dates.empty());
  std::cout << "XMQ_HOST_AES_CBC_DECRYPTS_BUT_NEVER_PUBLISHES_OK\n";
}
