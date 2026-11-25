#include "encrypted_input_gate.h"
#include <cassert>
#include <iostream>

int main() {
  xmq_security::EncryptedFrame input;
  xmq_runtime::XmqFrameResult out;
  input.inner_mvt = {"TCH", 0x95, 0x62};
  input.ciphertext.resize(16, 0xAB);
  assert(xmq_security::valid_aes128_cbc_shape(input));
  out.driver = "stale";
  assert(!xmq_security::decode_encrypted_pending(input, out));
  assert(out.driver.empty() && out.numeric.empty() && out.dates.empty());
  for (std::size_t n : {0U, 1U, 15U, 17U, 1025U}) {
    input.ciphertext.resize(n, 0xAB);
    assert(!xmq_security::valid_aes128_cbc_shape(input));
    out.driver = "stale";
    assert(!xmq_security::decode_encrypted_pending(input, out));
    assert(out.driver.empty() && out.numeric.empty() && out.dates.empty());
  }
  input.ciphertext.resize(1024, 0xAB);
  assert(xmq_security::valid_aes128_cbc_shape(input));
  assert(!xmq_security::decode_encrypted_pending(input, out));
  input.key.fill(0x42);
  input.iv.fill(0x27);
  assert(!xmq_security::decode_encrypted_pending(input, out));
  std::cout << "XMQ_ENCRYPTED_INPUT_GATE_FAIL_CLOSED_OK\n";
}
