"""Host-only AES-128-CBC primitive test using public NIST SP 800-38A vectors.

No keys from real meters. No ESPHome integration. CBC does not authenticate:
even a successful decryption must NOT be promoted to VerifiedCleartext.
"""
import subprocess

# NIST SP 800-38A, F.2.1, AES-128 CBC (four plaintext blocks).
KEY = "2b7e151628aed2a6abf7158809cf4f3c"
IV = "000102030405060708090a0b0c0d0e0f"
PLAIN = bytes.fromhex(
    "6bc1bee22e409f96e93d7e117393172a"
    "ae2d8a571e03ac9c9eb76fac45af8e51"
    "30c81c46a35ce411e5fbc1191a0a52ef"
    "f69f2445df4f9b17ad2b417be66c3710"
)
CIPHER = bytes.fromhex(
    "7649abac8119b246cee98e9b12e9197d"
    "5086cb9b507219ee95db113a917678b2"
    "73bed6b8e3c1743b7116e69e22229516"
    "3ff1caa1681fac09120eca307586e1a7"
)


def openssl_cbc(data, *, decrypt=False, key=KEY, iv=IV):
    cmd = [
        "openssl", "enc", "-aes-128-cbc",
        "-K", key, "-iv", iv, "-nopad",
        "-d" if decrypt else "-e",
    ]
    return subprocess.run(cmd, input=data, capture_output=True, check=True).stdout


assert openssl_cbc(PLAIN) == CIPHER
assert openssl_cbc(CIPHER, decrypt=True) == PLAIN
assert openssl_cbc(CIPHER[:16], decrypt=True) == PLAIN[:16]
assert openssl_cbc(CIPHER, decrypt=True, iv="ff" * 16) != PLAIN
assert openssl_cbc(CIPHER, decrypt=True, key="00" * 16) != PLAIN

# CBC is malleable: flipping a bit in the IV predictably flips the same
# plaintext bit, yet decryption still succeeds. This explicitly demonstrates
# why a plausible decrypted payload is NOT a verified/authenticated payload.
modified_iv = bytearray.fromhex(IV)
modified_iv[0] ^= 1
tampered_plain = openssl_cbc(CIPHER, decrypt=True, iv=modified_iv.hex())
assert tampered_plain[0] == (PLAIN[0] ^ 1)
assert tampered_plain[1:] == PLAIN[1:]

# A partial AES block must be rejected by the cryptographic primitive.
bad = subprocess.run(
    ["openssl", "enc", "-aes-128-cbc", "-K", KEY, "-iv", IV, "-nopad", "-d"],
    input=CIPHER[:-1], capture_output=True,
)
assert bad.returncode != 0

# This test deliberately does not call standalone_engine::decode or alter
# xmq_security::decode_encrypted_pending: publication is still denied.
print("XMQ_NIST_AES_CBC_HOST_VECTOR_OK_ENCRYPTED_PUBLICATION_DISABLED")
