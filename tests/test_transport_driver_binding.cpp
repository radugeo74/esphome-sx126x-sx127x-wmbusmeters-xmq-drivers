// Regression: transport signature and approved XMQ decoder must bind to
// the SAME driver even when YAML requests auto. Host only, public synthetic
// application fixtures, no radio and no Home Assistant writer.
#include "standalone_engine.h"
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

static void check(bool condition, const char *reason) {
  if (!condition) throw std::runtime_error(reason);
}
static bool decode_bound(const char *transport_driver,
                         const xmq_standalone::Input &input,
                         const std::string &selected_driver,
                         xmq_runtime::XmqFrameResult &output) {
  output = {};
  if (transport_driver == nullptr ||
      (selected_driver != "auto" && selected_driver != transport_driver))
    return false;
  if (!xmq_standalone::decode(input, output, transport_driver) ||
      output.driver != transport_driver) {
    output = {};
    return false;
  }
  return true;
}
int main() {
  try {
    using namespace xmq_runtime;
    using namespace xmq_standalone;
    const auto water = parse_hex("06702901006017030004000300000000000000000000000000000000000000000000");
    const auto heat = parse_hex("119F27020480048300C408F709143C003D341A2B0B2A0707000000000000062D114457563D71A1850000");
    Input w{Family::Water, {"TCH", 0x95, 0x62},
            ApplicationEncoding::OriginalIxml, water, Trust::VerifiedCleartext};
    Input h{Family::Heat, {"TCH", 0x69, 0x80},
            ApplicationEncoding::OriginalIxml, heat, Trust::VerifiedCleartext};
    XmqFrameResult out;
    const char *water_transport = match_transport_signature(
        0x95, 0x62, 0xa2, water.data(), water.size());
    const char *heat_transport = match_transport_signature(
        0x69, 0x80, 0xa0, heat.data(), heat.size());
    check(water_transport != nullptr && std::string(water_transport) == "mkradio4",
          "water transport signature");
    check(heat_transport != nullptr && std::string(heat_transport) == "fhkvdataiii",
          "heat transport signature");
    check(decode_bound(water_transport, w, "auto", out) && out.driver == "mkradio4",
          "water auto must bind to transport driver");
    check(decode_bound(heat_transport, h, "auto", out) && out.driver == "fhkvdataiii",
          "heat auto must bind to transport driver");
    check(decode_bound(water_transport, w, "mkradio4", out),
          "explicit matching driver rejected");
    out.driver = "stale";
    check(!decode_bound(water_transport, w, "fhkvdataiii", out) && out.driver.empty(),
          "explicit mismatched driver accepted");
    out.driver = "stale";
    check(!decode_bound(heat_transport, w, "auto", out) &&
          out.driver.empty() && out.numeric.empty(),
          "water application accepted against heat transport");
    out.driver = "stale";
    check(!decode_bound(water_transport, h, "auto", out) &&
          out.driver.empty() && out.numeric.empty(),
          "heat application accepted against water transport");
    out.driver = "stale";
    check(!decode_bound(nullptr, w, "auto", out) && out.driver.empty(),
          "unapproved transport admitted");
    w.trust = Trust::Ciphertext;
    check(!decode_bound(water_transport, w, "auto", out) &&
          out.driver.empty() && out.numeric.empty(), "ciphertext admitted");
    std::cout << "XMQ_TRANSPORT_DRIVER_BOUND_FAIL_CLOSED_OK\n";
    return 0;
  } catch (const std::exception &err) {
    std::cerr << err.what() << '\n';
    return 1;
  }
}
