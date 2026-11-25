"""Negative fixture policy tests; no cryptography or on-device decoder."""
import copy
import json
from tempfile import TemporaryDirectory
import importlib.util
from pathlib import Path

root = Path(__file__).resolve().parents[1]
modpath = root / "tests" / "encrypted_fixture_contract.py"
spec = importlib.util.spec_from_file_location("encrypted_fixture_contract", modpath)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
fixture = module.load_pending_fixture(root / "tests" / "fixtures" / "encrypted" / "synthetic_pending.json")
assert fixture["integrity_evidence"] == "not_verified"
assert fixture["key_reference"] == "not_in_repository"
def reject(**changes):
    candidate = copy.deepcopy(fixture)
    candidate.update(changes)
    try:
        module.validate_pending_fixture(candidate)
    except ValueError:
        return
    raise AssertionError("Unsafe encrypted fixture accepted: " + repr(changes))

reject(aes_key="0123456789abcdef0123456789abcdef")
reject(key="00112233445566778899aabbccddeeff")
reject(plaintext="hello")
reject(source="private_meter_capture")
reject(source="public_reference")
reject(reference_url="https://example.com/claim")
reject(source="public_reference", reference_url="http://example.com/frame")
reject(source="public_reference", reference_url="https://user:pass@example.com/frame")
reject(source="public_reference", reference_url="https://example.com/frame?key=secret")
good_public = copy.deepcopy(fixture)
good_public.update(source="public_reference", reference_url="https://example.com/documented-fixture")
assert module.validate_pending_fixture(good_public) is good_public
with TemporaryDirectory() as tmp:
    duplicate = Path(tmp) / "duplicate.json"
    duplicate.write_text(json.dumps(fixture)[:-1] + ', "ci": 7}', encoding="utf-8")
    try:
        module.load_pending_fixture(duplicate)
    except ValueError as e:
        assert "Duplicate" in str(e)
    else:
        raise AssertionError("Duplicate CI field accepted")
reject(link_mode="UNKNOWN")
reject(manufacturer="INVALID")
reject(version=-1)
reject(device_type=256)
reject(ci=True)
reject(access_number=999)
reject(ciphertext_hex="ab" * 15)
reject(ciphertext_hex="ab" * 65 * 16)
reject(ciphertext_hex="qq" * 16)
reject(security_configuration_hex="99")
reject(security_configuration_hex="GGGG")
reject(iv_derivation="assumed")
reject(integrity_evidence="verified")
reject(key_reference="real_key_in_yaml")
candidate = dict(fixture)
del candidate["access_number"]
try:
    module.validate_pending_fixture(candidate)
except ValueError:
    pass
else:
    raise AssertionError("Missing access number was accepted")
print("XMQ_ENCRYPTED_FIXTURE_CONTRACT_FAIL_CLOSED_OK")
