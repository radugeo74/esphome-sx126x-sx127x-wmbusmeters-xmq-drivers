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
