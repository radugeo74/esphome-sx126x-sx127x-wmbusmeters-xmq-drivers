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

## Experimental YAML driver selection (supported formats only)

In `experimental/xmq-auto-drivers`, `xmq_meter` now accepts optional
`driver: auto` (default), `driver: fhkvdataiii` for heat, and
`driver: mkradio4` for water. The explicit driver is checked against the
meter family and the driver's actual MVT detection. Unknown, mismatched,
or unvalidated drivers fail closed; no stale sensor values are published.

Example:

```yaml
xmq_meter:
  - radio_id: receiver
    meter_id: 0x12345000
    family: heat
    driver: fhkvdataiii
    current_hca:
      name: Example Heat
```

The independent `mkradio4a.xmq` is discoverable in the generated
catalog but is **not** enabled for production decoding by this change;
its security envelope, field projection and fixtures need separate tests.
No claim is made of universal automatic decoding for arbitrary XMQ files.

### Auto selection from inner MVT (validated profiles)

`driver: auto` now asks `DriverRegistry::select()` to choose the matching
validated driver from the inner manufacturer/version/type (MVT).
`family` is checked as an additional contract, not used as the driver
selection mechanism. An unknown or ambiguous MVT and a family mismatch
fail closed without publishing sensor values. The generated catalog can
contain additional `.xmq` definitions, but no newly imported driver is
allowed to publish until its transport/security and output-field profile
is reviewed and explicitly enabled in the validated registry. Existing
`driver: fhkvdataiii` and `driver: mkradio4` remain supported.

### Reviewed XMQ profiles (experimental)

`validated_profiles.json` holds the reviewed driver names, meter families and
required numeric output fields. The C++ registry is now constructed from the
auto-generated profile catalog, not a handwritten list. Updating one .xmq
requires no engine changes. New .xmq files appear in the source catalog but
cannot publish without an independently reviewed profile, security envelope,
and verified output mapping. The radio adapter still accepts only the proven
proprietary Techem T1 envelopes.

### Family validation in YAML (experimental)

When `driver:` is explicit, ESPHome validation rejects an unapproved driver or a
mismatch between `driver` and `family` **before compilation**. `driver: auto`
remains available; its actual selection is performed from MVT in the reviewed
runtime registry. This check does not broaden the radio/security adaptor.

### Reviewed transport signatures (experimental)

The exact proprietary Techem T1 envelope allowlist lives in
`transport_signatures.json` and is compiled into `xmq_driver_sources.h`.
This replaces hard-coded A0/A2/version/type/application-prefix branches in
`xmq_meter.cpp`, with equivalent approved formats. A new `.xmq` file
alone cannot authorize a transport envelope or publication. Signatures are
**not** cryptographic authentication; encrypted/security modes need a
separate reviewed decrypt-and-verify path before being enabled.

### Explicit transport security policy

`transport_signatures.json` now distinguishes `security: clear_form` from
`security: encrypted_pending`. The runtime matcher accepts **only** the
reviewed `clear_form` signatures. Any `encrypted_pending` signature is
compiled for future research but cannot reach the XMQ decoder or publish
sensors. An unknown security mode fails code generation. This adds no
cryptographic authentication or decryption; such support must be implemented
and tested independently before changing the gate.
