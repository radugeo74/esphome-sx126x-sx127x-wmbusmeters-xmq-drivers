# ESPHome SX126x / SX127x wM-Bus — XMQ standalone

Minimal copy of the **functional** XMQ-only pipeline from
[`radugeo74/esphome-sx1262`](https://github.com/radugeo74/esphome-sx1262),
branch `experimental/xmq-standalone-no-legacy`, commit
`d7e9fdffcbde3e51f0fa85b79b2ecc56bd597e98`.

## Included components

- `components/sx126x` — Heltec native FSK T1/C1 PHY
- `components/sx127x` — LILYGO experimental native FIFO T1/C1 PHY (hardware performance unchanged)
- `components/wmbus_radio` — independent 3-of-6 and Format A/B CRC validation, 60-second PHY stats
- `components/xmq_meter` — XMQ application engine and bundled XMQ driver sources, ESPHome sensor projection

The bundled XMQ driver source definitions include `fhkvdataiii`, `mkradio4`,
and `mkradio4a`. The current **production** standalone decoder selects
`fhkvdataiii` for heat and `mkradio4` for water; `mkradio4a` is bundled
but **not enabled** for the 12 existing meter subscriptions.

**Deliberately excluded:** `wmbus_common`, legacy `wmbus_meter`, old
`driver_*.cc`, unused experiments, old workflows, and any private meter IDs,
keys, Wi-Fi/API/OTA credentials or actual production YAML.

## ESPHome configuration

```yaml
external_components:
  - source: github://radugeo74/esphome-sx126x-sx127x-wmbusmeters-xmq-drivers@main
    components: [sx126x, wmbus_radio, xmq_meter]
```

For a LILYGO SX1276-only configuration, use
`components: [sx127x, wmbus_radio, xmq_meter]` (or omit `xmq_meter` if no
meters are configured). The actual SPI/radio settings and your private IDs and
sensor names remain in the local device YAML. **Do not use CI test YAML on
physical devices; credentials and IDs in it are synthetic.**

## Tests and rollout

Single workflow: `.github/workflows/standalone.yml` builds the 12-meter
synthetic Heltec firmware and the SX1276 radio-only LILYGO fixture, and runs
standalone XMQ and CRC regression tests on ESPHome 2026.11.0.

The original functional firmware remains on devices until GitHub CI is green
and the device's private YAML is switched to the new repository and validated.
Never publish production meter addresses or credentials.

## Driver files — independent XMQ sources

**Source of truth:** `components/xmq_meter/drivers/<driver>.xmq`.
Every driver is individually editable/replacable. Existing examples:

- `fhkvdataiii.xmq` — current heat profile
- `mkradio4.xmq` — current water profile
- `mkradio4a.xmq` — available source, not active in current firmware

`components/xmq_meter/generate_drivers.py` generates
`xmq_driver_sources.h` from `drivers/*.xmq` during ESPHome component loading.
The generated header is **not committed**. Do not edit it. The engine's
existing driver-loading API remains unchanged; no legacy driver copies.
The generator validates that the file basename matches the driver `name`.
Adding an arbitrary new file makes its `source_<name>()` available, but
**does not automatically add meter-family routing or publish new fields**:
those are separate configuration/engine changes when needed.

Workflow validates independent replacement of a single driver without
changing the generated function bodies of other drivers.

## Experimental development: auto-generated driver catalog

This branch generates a catalog from all `drivers/*.xmq` files and validates
its entries with host tests. The standalone engine now looks up existing
`fhkvdataiii` and `mkradio4` sources by catalog name rather than referencing
individual C++ source functions. This **does not yet enable new meter types
through YAML**. The stable `main` branch is unchanged; do not flash this
experimental branch until its CI and hardware testing are complete.
