# Pending encrypted wM-Bus fixture intake

This directory contains only a **synthetic, non-decodable metadata example**.
It is not a real meter capture and makes no claim about a particular OMS
security mode, IV, integrity algorithm, or sensor value.

When we obtain a legitimately shareable public-reference test telegram,
record its actual manufacturer/version/type, link mode, CI, access number,
security-configuration bytes, ciphertext, and reference provenance. Do **not**
fill unknown fields from assumptions: the fixture contract accepts only
`unknown` or `documented_not_implemented` for IV derivation and requires
`integrity_evidence: not_verified` while the adapter remains closed.

Never store AES keys, real meter IDs, plaintext containing private readings,
home-network credentials, or private device identifiers in the repository.
Until protocol-specific validation and secure key provisioning are reviewed,
these fixtures are **test inputs only** and cannot unlock sensor publishing.

Public-reference fixtures must include a verifiable `https://` URL without
credentials, query parameters or fragments. Synthetic fixtures must set
`reference_url: null`. The loader rejects duplicate JSON keys, so a second
`ci` or `security_configuration_hex` cannot silently override the first.
A source URL documents provenance only; it does not verify the telegram or
provide authorization to publish.

CI scans **all** `.json` entries in this directory (rather than only the
synthetic sample), rejects duplicate metadata/ciphertext tuples and applies
the strict fixture contract to every entry. It does not fetch provenance URLs
or infer any validated OMS security mode from the fixture contents.
