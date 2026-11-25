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

### Pending encrypted input boundary

`encrypted_input_gate.h` defines a host-tested AES-128-CBC-shaped input
contract (key, IV, ciphertext). It checks only length and block alignment.
**No decryption, integrity/authentication proof, meter-key binding, or replay
protection is implemented.** The pending decoder unconditionally rejects and
clears all output; it is not wired to the live radio. Never place real meter
keys in this repository or CI fixtures. Do not mark ciphertext as verified
plaintext. Later implementation requires protocol-specific authenticated
verification (or independently validated integrity strategy) before any
sensor publication.

### Host-only AES-128-CBC reference vector test

`tests/test_aes_cbc_nist_vector.py` checks OpenSSL against the published
NIST SP 800-38A F.2.1 four-block AES-128-CBC vectors. It additionally checks
wrong key/IV, truncated ciphertext and the predictable IV bit-flip effect.
This demonstrates CBC **malleability**, so decryption alone cannot establish
telegram authenticity, integrity, meter binding, freshness or authorization to
publish. No encrypted data is passed to `standalone_engine`; the pending
runtime adapter continues to reject all encrypted telegrams. The actual
OMS security mode, IV construction, key derivation and replay policy are
still unimplemented pending protocol-specific reference frames.

### Host-only C++ AES-CBC primitive probe

`tests/test_aes_cbc_host_probe.cpp` exercises native OpenSSL EVP AES-128-CBC
against the public NIST vector, including a manipulated IV and invalid block
length. Its result type is deliberately named `UnauthenticatedPlaintext`;
cryptographic transformation does not establish the correct wM-Bus security
mode, key/IV derivation, integrity or replay protection. This probe is kept
in `tests/`, is **never linked into firmware**, and the runtime encrypted
input gate still unconditionally refuses sensor publication.

### AES-CMAC (RFC 4493) conformance — host tests only

`tests/test_aes_cmac_rfc4493.cpp` checks the OpenSSL 3 EVP_MAC CMAC
primitive against RFC 4493 section 4 vectors (0/16/40/64 bytes), detects a
changed message, checks invalid key length and verifies the encrypted runtime
gate still rejects output. Public test key only. This **does not assert** that
any supported meter uses AES-CMAC: wM-Bus security mode, authenticated data,
message layout, tag truncation, key binding and replay validation remain
unverified, so no protocol MAC verifier is wired into firmware.

### Transport-to-driver binding for auto selection

After a T1 clear-form transport signature is accepted, the decoder is now
explicitly constrained to the **same reviewed driver** even for YAML
`driver: auto`. MVT detection, required primary fields, and the projected
result must agree before any HA sensor publish. Host regression checks cover
both approved meter families, explicit mismatch, cross-family payloads,
unknown transport and ciphertext rejection. This does not implement or enable
encrypted telegram decoding.

### Single shared transport-driver binding implementation

`transport_driver_binding.h` now contains the actual fail-closed binding
used in **both** the ESPHome frame handler and host regression test. The
previous test-local copy has been removed, so tests exercise the same
implementation that controls publication. Unknown transport, mismatched
explicit driver, mismatched MVT/family and ciphertext all clear output and
reject before any sensor publish. No encryption features were enabled.

### Transport prefix collision guard

The generated transport allowlist now rejects **overlapping signatures**
sharing version/type/CI, including exact duplicates, shorter/longer matching
prefixes, different drivers and clear-form versus encrypted-pending entries.
This prevents a shorter clear-form signature from bypassing the future
`encrypted_pending` gate. The existing reviewed 14 signatures are unchanged;
CI checks both negative collisions and a non-overlapping pending entry.

### Validated driver transport coverage

The driver generator rejects a reviewed profile if it has no admissible
`clear_form` transport signature, including profiles whose signatures were
all changed to `encrypted_pending`. This prevents an apparently enabled
YAML driver from silently having no approved transport. It does not authorize
any new driver or enable AES decoding. CI uses temporary fixtures for the
negative cases and leaves the 14 reviewed signatures unchanged.

### Static transport/MVT consistency check

The existing CI workflow now checks each approved driver’s `detect.mvt`
entries against the set of MVT tuples admitted by its `clear_form`
transport signatures. A missing or invented allowed MVT fails the build.
This test uses no keys and makes no changes to the radio receiver or firmware.

### Fail-closed meter family enumeration

The standalone decoder now rejects enum values other than explicit `Heat`
and `Water` before consulting the registry. Previously, an out-of-range
family value could be treated as Water in the family comparison. Regression
checks use a valid water payload with an invalid family and require empty
output (including any stale driver, numeric and date values), then verify
that valid Water still decodes. No new driver was approved.

### Proprietary encoding boundary

The transport-bound decoder only accepts `OriginalIxml` application
encoding for the currently reviewed proprietary TCH A0/A2 clear-form
signatures. `StandardDv` and unknown encoding enum values are rejected
before the XMQ engine. Host checks also cover empty/oversize applications
and require stale output to be cleared on failure. Standard DV decoding
remains available in the independent XMQ engine for future explicitly
reviewed transports; no encrypted support is enabled.

### mkradio4a candidate integration (CI 0x72, no key)

`mkradio4a_candidate.h` now connects the full upstream CI 0x72 envelope,
validated **inner** BCD meter identity, independent StandardDv XMQ driver,
and primary-readiness gate. Acceptance requires both `target_m3` and a
valid calendar `target_date` before a result can leave the candidate.
Host regressions check both original warm/cold specimens, wrong inner ID,
missing volume/date, invalid date and stale-output clearing. The
candidate does not register mkradio4a for live sensors and does not decode
the encrypted manufacturer-specific tail. No new real meter keys are needed.

### mkradio4a experimental ESPHome CI72 output

The existing `xmq_meter` now supports explicit `driver: mkradio4a`
for `family: water` using the bounded CI72 candidate with the **inner**
BCD meter ID. It publishes `target_m3` (numeric), `target_date` (text
sensor in YYYY-MM-DD) and optional RSSI, only if the volume and date are
both present and valid. The synthetic Heltec CI build includes this opt-in
instance. This is **not enabled for `driver: auto`**, not part of the
manifest-approved proprietary signatures, and does not interpret encrypted
telegrams. Do not flash the build-only CI YAML or change the stable main.
