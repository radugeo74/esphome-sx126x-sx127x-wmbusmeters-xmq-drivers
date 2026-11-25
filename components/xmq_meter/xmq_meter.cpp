#include "xmq_meter.h"
#include "transport_driver_binding.h"
#include <cmath>
#include <utility>
namespace esphome { namespace xmq_meter {
static const char *const TAG = "xmq_meter";

void Meter::set_radio(wmbus_radio::Radio *radio) {
  this->radio_ = radio;
  radio->add_frame_handler([this](wmbus_radio::Frame *frame) {
    this->handle_frame_(frame);
  });
}

void Meter::handle_frame_(wmbus_radio::Frame *frame) {
  if (frame == nullptr || frame->link_mode() != wmbus_radio::LinkMode::T1) return;
  // The radio already checked PHY encoding and DLL CRC. No legacy Telegram
  // parsing/driver is allowed. Proprietary CI A0/A2 is admitted ONLY when
  // its exact known clear-form envelope and assigned ID match.
  const auto &dll = frame->data();
  if (dll.size() < 20 || dll.size() > 256 || dll.size() != size_t(dll[0]) + 1 ||
      dll[1] != 0x44 || dll[2] != 0x68 || dll[3] != 0x50) return;
  const uint32_t address = uint32_t(dll[4]) |
      uint32_t(dll[5]) << 8 | uint32_t(dll[6]) << 16 |
      uint32_t(dll[7]) << 24;
  if (address != this->meter_id_) return;
  const bool water = !this->heat_;
  // Only allow reviewed clear-form transport signatures generated from
  // transport_signatures.json. These are format checks, NOT a cryptographic MAC.
  const char *transport_driver = xmq_runtime::match_transport_signature(
      dll[8], dll[9], dll[10], dll.data() + 11, dll.size() - 11);
  if (transport_driver == nullptr) {
    ESP_LOGW(TAG, "XMQ frame rejected: unapproved transport envelope");
    return;
  }
  // Exact known proprietary clear-form signatures only. They are NOT
  // cryptographic proof: these water/heat formats have no independent MAC.
  xmq_standalone::Input in{
      water ? xmq_standalone::Family::Water : xmq_standalone::Family::Heat,
      {"TCH", dll[8], dll[9]},
      xmq_runtime::ApplicationEncoding::OriginalIxml,
      std::vector<uint8_t>(dll.begin() + 11, dll.end()),
      xmq_standalone::Trust::VerifiedCleartext};
  xmq_runtime::XmqFrameResult output;
  const uint32_t start = micros();
  // Bind the *transport-approved* driver to the MVT and XMQ field
  // projection. In auto mode never independently choose a different
  // driver after a proprietary transport signature has been admitted.
  if (!xmq_standalone::decode_transport_bound(
          transport_driver, in, this->driver_, output)) {
    ESP_LOGW(TAG, "XMQ transport/driver binding failed: no sensor publication");
    return;
  }
  frame->mark_as_handled();
  if (this->radio_ != nullptr) this->radio_->note_xmq_decoded(water);
  const uint32_t elapsed = micros() - start;
  const float rssi = float(frame->rssi());
  this->defer([this, output = std::move(output), rssi]() {
    for (const auto &entry : this->sensors_) {
      if (entry.first == "rssi_dbm") {
        entry.second->publish_state(rssi);
        continue;
      }
      const auto found = output.numeric.find(entry.first);
      if (found != output.numeric.end() && std::isfinite(found->second.value))
        entry.second->publish_state(float(found->second.value));
    }
  });
  ESP_LOGD(TAG, "XMQ direct decoded family=%s decode_us=%u; no legacy parser",
           water ? "water" : "heat", static_cast<unsigned>(elapsed));
}
}} // namespace esphome::xmq_meter
