// mkradio4a first integration stage: execute BOTH real upstream example
// application telegrams against the independent XMQ StandardDv decoder.
// This is not yet an on-device CI 0x72 / inner MVT transport adapter.
#include "xmq_frame_bridge.h"
#include "xmq_driver_sources.h"
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

static void require(bool ok, const char *message) {
  if (!ok) throw std::runtime_error(message);
}
int main() {
  try {
    using namespace xmq_runtime;
    const auto *source = source_by_name("mkradio4a");
    require(source != nullptr, "mkradio4a source absent");
    DriverRegistry registry({load_driver(source)});
    // Both specimens occur in the upstream driver's own tests. The preceding
    // DLL/TPL (including the outer TCH manufacturer) is deliberately excluded.
    const auto warm = parse_hex(
      "4315A10000426CBF2C0F542CF2DD8BEC869511B2DB8301C3ABA390FB4FDB6F1144DA1F3897DD55F2AD0D194F68510FF8FADFB9");
    const auto cold = parse_hex(
      "4315F00200426CBF2C0FEE456BF6F802216503E25EB73E9377D54F672681B76C469696E4C7BCCC9072CC79F712360FC3F57D85");
    const auto verify = [&](const std::vector<uint8_t> &payload,
                            double expected, const Mvt &meter) {
      const auto result = project_verified_application(
          registry, meter, ApplicationEncoding::StandardDv, payload, "mkradio4a");
      require(result.driver == "mkradio4a", "wrong driver selected");
      auto target = result.numeric.find("target_m3");
      require(target != result.numeric.end(), "missing mkradio4a target volume");
      require(target->second.value > expected - 0.0001 &&
              target->second.value < expected + 0.0001, "incorrect target volume");
      auto date = result.dates.find("target_date");
      require(date != result.dates.end() && date->second == "2021-12-31",
              "incorrect target date");
    };
    verify(warm, 16.1, {"TCH",0x95,0x37});
    verify(cold, 75.2, {"TCH",0x95,0x37});
    verify(warm, 16.1, {"HYD",0xfe,0x06});
    std::cout << "XMQ_MKRADIO4A_UPSTREAM_STANDARD_DV_FIXTURES_OK\n";
  } catch (const std::exception &e) {
    std::cerr << "FAIL: " << e.what() << '\n';
    return 1;
  }
}
