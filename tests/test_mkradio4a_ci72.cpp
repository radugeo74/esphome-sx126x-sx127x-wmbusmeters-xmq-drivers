// Decode both complete mkradio4a upstream telegrams via CI 0x72 adapter.
// Only two clear data records (target volume/date) are admitted. No radio,
// AES decryption, or HA publication occurs in this test.
#include "mkradio4a_ci72.h"
#include "xmq_driver_sources.h"
#include <cmath>
#include <iostream>
#include <stdexcept>
#include <vector>
static void require(bool ok, const char *message) {
  if (!ok) throw std::runtime_error(message);
}
int main() {
  try {
    using namespace xmq_runtime;
    using namespace xmq_standalone;
    const auto warm = parse_hex(
      "4B44685036494600953772253895662423FE064E0030052F2F"
      "4315A10000426CBF2C0F542CF2DD8BEC869511B2DB8301C3ABA390FB4FDB6F1144DA1F3897DD55F2AD0D194F68510FF8FADFB9");
    const auto cold = parse_hex(
      "4B4468508644710095377202007701A85CFE078A0030052F2F"
      "4315F00200426CBF2C0FEE456BF6F802216503E25EB73E9377D54F672681B76C469696E4C7BCCC9072CC79F712360FC3F57D85");
    DriverRegistry registry({load_driver(source_by_name("mkradio4a"))});
    const auto verify = [&](const std::vector<std::uint8_t> &raw,
                            std::uint32_t id, double volume) {
      Input input{};
      require(parse_mkradio4a_ci72(raw,id,input), "rejected known upstream CI 72 frame");
      require(input.trust == Trust::VerifiedCleartext &&
              input.encoding == ApplicationEncoding::StandardDv &&
              input.application.size() == 10, "incorrect trusted clear prefix");
      const auto out = project_verified_application(
          registry,input.inner_mvt,input.encoding,input.application,"mkradio4a");
      const auto v = out.numeric.find("target_m3");
      const auto d = out.dates.find("target_date");
      require(v != out.numeric.end() && std::abs(v->second.value-volume)<0.0001,
              "incorrect target volume");
      require(d != out.dates.end() && d->second == "2021-12-31",
              "incorrect target date");
      Input rejected{};
      require(!parse_mkradio4a_ci72(raw,id^1,rejected) &&
              rejected.trust == Trust::Unknown &&
              rejected.application.empty(), "wrong inner ID admitted");
      auto tampered=raw;
      tampered[11]=0xFA;
      require(!parse_mkradio4a_ci72(tampered,id,rejected),
              "non-BCD inner ID admitted");
      tampered=raw; tampered[21]=0x00;
      require(!parse_mkradio4a_ci72(tampered,id,rejected),
              "unsupported security configuration admitted");
      tampered=raw; tampered[34]=0x00;
      require(!parse_mkradio4a_ci72(tampered,id,rejected),
              "encrypted tail separator missing");
      tampered=raw; tampered[9]=0x62;
      require(!parse_mkradio4a_ci72(tampered,id,rejected),
              "wrong outer type admitted");
      tampered=raw; tampered[0]=0x4a;
      require(!parse_mkradio4a_ci72(tampered,id,rejected),
              "bad DLL length admitted");
    };
    verify(warm,0x66953825,16.1);
    verify(cold,0x01770002,75.2);
    std::cout << "XMQ_MKRADIO4A_CI72_INNER_ID_AND_CLEAR_FIELDS_OK\n";
    return 0;
  } catch (const std::exception &e) {
    std::cerr << "FAIL: " << e.what() << '\n';
    return 1;
  }
}
