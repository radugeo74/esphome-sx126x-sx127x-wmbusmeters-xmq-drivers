#include "xmq_driver_sources.h"
#include <cassert>
#include <cstring>
#include <iostream>

int main() {
  using xmq_runtime::match_transport_signature;
  std::size_t count = 0;
  const auto *signatures = xmq_runtime::transport_signature_catalog(count);
  assert(signatures != nullptr && count == 14);
  for (std::size_t i = 0; i < count; ++i) {
    const auto &s = signatures[i];
    assert(s.prefix_len >= 1 && s.prefix_len <= 3);
    assert(s.security_mode == 0);
    const auto *match = match_transport_signature(
        s.version, s.type, s.ci, s.prefix, s.prefix_len);
    assert(match != nullptr && std::strcmp(match, s.driver) == 0);
    assert(match_transport_signature(s.version, s.type, s.ci, s.prefix, 0) == nullptr);
  }
  const unsigned char heat[] = {0x11, 0x99, 0x88};
  const unsigned char water[] = {0x06, 0x3e, 0x35};
  const unsigned char bad_water[] = {0x06, 0x3e, 0x36};
  assert(std::strcmp(match_transport_signature(0x69, 0x80, 0xa0, heat, sizeof(heat)), "fhkvdataiii") == 0);
  assert(std::strcmp(match_transport_signature(0x95, 0x62, 0xa2, water, sizeof(water)), "mkradio4") == 0);
  assert(match_transport_signature(0x95, 0x62, 0xa2, bad_water, sizeof(bad_water)) == nullptr);
  assert(match_transport_signature(0x95, 0x62, 0xa0, water, sizeof(water)) == nullptr);
  assert(match_transport_signature(0x95, 0x37, 0xa2, water, sizeof(water)) == nullptr);
  assert(match_transport_signature(0x95, 0x62, 0xa2, nullptr, 3) == nullptr);
  std::cout << "XMQ_TRANSPORT_SIGNATURES_OK" << '\n';
}
