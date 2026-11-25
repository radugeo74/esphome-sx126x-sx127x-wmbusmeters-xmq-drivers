// Full CI72 -> approved-shape meter ID -> XMQ -> required numeric AND date.
// An absent/invalid field must never produce a partial publishable result.
#include "mkradio4a_candidate.h"
#include <cmath>
#include <iostream>
#include <stdexcept>

static void check(bool ok, const char *reason) {
  if (!ok) throw std::runtime_error(reason);
}

int main() {
  using namespace xmq_runtime;
  using namespace xmq_standalone;
  try {
    const auto warm = parse_hex(
      "4B44685036494600953772253895662423FE064E0030052F2F"
      "4315A10000426CBF2C0F542CF2DD8BEC869511B2DB8301C3ABA390FB4FDB6F1144DA1F3897DD55F2AD0D194F68510FF8FADFB9");
    const auto cold = parse_hex(
      "4B4468508644710095377202007701A85CFE078A0030052F2F"
      "4315F00200426CBF2C0FEE456BF6F802216503E25EB73E9377D54F672681B76C469696E4C7BCCC9072CC79F712360FC3F57D85");
    const auto verify = [&](const std::vector<std::uint8_t> &frame,
                            std::uint32_t id, double expected) {
      XmqFrameResult result{};
      check(decode_mkradio4a_ci72_candidate(frame, id, result),
            "reviewed upstream mkradio4a CI72 candidate was rejected");
      check(result.driver == "mkradio4a", "unexpected XMQ driver");
      const auto vol = result.numeric.find("target_m3");
      const auto date = result.dates.find("target_date");
      check(vol != result.numeric.end() && std::abs(vol->second.value - expected) < 0.0001,
            "target_m3 absent/incorrect");
      check(date != result.dates.end() && date->second == "2021-12-31",
            "target_date absent/incorrect");
      // The date must be a valid calendar date, not merely a formatted string.
      check(valid_primary_iso_date(date->second), "invalid calendar value");
      result.driver = "stale";
      check(!decode_mkradio4a_ci72_candidate(frame, id ^ 1u, result) &&
            result.driver.empty() && result.numeric.empty() && result.dates.empty(),
            "wrong inner ID accepted or stale readings preserved");
      auto damaged = frame;
      damaged[32] = 0; damaged[33] = 0; // date becomes invalid
      check(!decode_mkradio4a_ci72_candidate(damaged, id, result) &&
            result.driver.empty() && result.numeric.empty() && result.dates.empty(),
            "invalid OMS date accepted");
      damaged = frame;
      damaged[30] = 0x00; // remove date DIF
      check(!decode_mkradio4a_ci72_candidate(damaged, id, result) &&
            result.driver.empty() && result.numeric.empty() && result.dates.empty(),
            "missing date accepted");
      damaged = frame;
      damaged[25] = 0x00; // remove volume DIF
      check(!decode_mkradio4a_ci72_candidate(damaged, id, result) &&
            result.driver.empty() && result.numeric.empty() && result.dates.empty(),
            "missing volume accepted");
    };
    verify(warm, 0x66953825, 16.1);
    verify(cold, 0x01770002, 75.2);
    std::cout << "XMQ_MKRADIO4A_CI72_CANDIDATE_VOLUME_AND_DATE_READY_OK\n";
    return 0;
  } catch (const std::exception &err) {
    std::cerr << "FAIL: " << err.what() << '\n';
    return 1;
  }
}
