#include "xmq_driver_sources.h"
#include "xmq_driver_registry.h"
#include <cassert>
#include <cstring>
#include <iostream>
#include <string>
#include <vector>

int main() {
  std::size_t count = 0;
  const auto *sources = xmq_runtime::driver_catalog(count);
  assert(count == 3);
  std::vector<xmq_runtime::Driver> drivers;
  for (std::size_t i = 0; i < count; ++i) {
    assert(sources[i].name != nullptr);
    assert(sources[i].source != nullptr);
    assert(xmq_runtime::source_by_name(sources[i].name) == sources[i].source);
    auto driver = xmq_runtime::load_driver(sources[i].source);
    assert(driver.name == sources[i].name);
    drivers.push_back(std::move(driver));
  }
  assert(xmq_runtime::source_by_name("nonexistent") == nullptr);
  assert(xmq_runtime::source_by_name(nullptr) == nullptr);
  assert(xmq_runtime::source_by_name("mkradio4") != nullptr);
  assert(xmq_runtime::source_by_name("mkradio4a") != nullptr);
  assert(xmq_runtime::source_by_name("fhkvdataiii") != nullptr);
  // Existing MVT selection must be deterministic where unambiguous.
  xmq_runtime::DriverRegistry registry(std::move(drivers));
  assert(registry.select({"TCH", 0x69, 0x80}).name == "fhkvdataiii");
  assert(registry.select({"TCH", 0x95, 0x62}).name == "mkradio4");
  std::cout << "XMQ_GENERATED_DRIVER_CATALOG_OK count=" << count << '\n';
}
