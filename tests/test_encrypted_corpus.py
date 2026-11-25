"""Test corpus-wide fixture checks against duplicate and unsafe additions."""
import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "tests" / "scan_encrypted_fixtures.py"
spec = importlib.util.spec_from_file_location("scan_encrypted_fixtures", path)
scanner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scanner)

source = ROOT / "tests" / "fixtures" / "encrypted" / "synthetic_pending.json"
with TemporaryDirectory() as d:
    directory = Path(d)
    (directory / "one.json").write_bytes(source.read_bytes())
    assert scanner.validate_corpus(directory) == 1

    (directory / "duplicate.json").write_bytes(source.read_bytes())
    try:
        scanner.validate_corpus(directory)
    except ValueError as exc:
        assert "Duplicate" in str(exc)
    else:
        raise AssertionError("Duplicate ciphertext was accepted")
    (directory / "duplicate.json").unlink()

    # Future fixture additions cannot bypass the strict loader.
    bad = json.loads(source.read_text(encoding="utf-8"))
    bad["integrity_evidence"] = "verified"
    (directory / "unsafe.json").write_text(json.dumps(bad), encoding="utf-8")
    try:
        scanner.validate_corpus(directory)
    except ValueError as exc:
        assert "verified authenticity" in str(exc)
    else:
        raise AssertionError("Unsafe corpus entry accepted")
    (directory / "unsafe.json").unlink()
    (directory / "one.json").unlink()
    try:
        scanner.validate_corpus(directory)
    except ValueError as exc:
        assert "Empty" in str(exc)
    else:
        raise AssertionError("Empty corpus was accepted")

assert scanner.validate_corpus(ROOT / "tests" / "fixtures" / "encrypted") >= 1
print("XMQ_ENCRYPTED_CORPUS_NEGATIVE_TESTS_OK")
