"""Check every pending encrypted reference fixture, not just the example.

The corpus is metadata-only. Validation is deliberately offline: URLs are
provenance declarations, not claims of authenticated telegrams.
"""
import hashlib
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "tests" / "encrypted_fixture_contract.py"
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "encrypted"

spec = importlib.util.spec_from_file_location("encrypted_fixture_contract", CONTRACT_PATH)
contract = importlib.util.module_from_spec(spec)
spec.loader.exec_module(contract)


def validate_corpus(folder):
    paths = sorted(Path(folder).glob("*.json"))
    if not paths:
        raise ValueError("Empty encrypted fixture corpus")
    seen = set()
    for path in paths:
        fixture = contract.load_pending_fixture(path)
        fingerprint = (
            fixture["manufacturer"], fixture["version"], fixture["device_type"],
            fixture["ci"], fixture["access_number"],
            fixture["security_configuration_hex"].lower(),
            hashlib.sha256(bytes.fromhex(fixture["ciphertext_hex"])).hexdigest(),
        )
        if fingerprint in seen:
            raise ValueError("Duplicate encrypted fixture metadata/ciphertext")
        seen.add(fingerprint)
    return len(paths)


if __name__ == "__main__":
    print("XMQ_PENDING_ENCRYPTED_CORPUS_OK count=" + str(validate_corpus(FIXTURE_DIR)))
