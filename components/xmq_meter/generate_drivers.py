"""Generate XMQ C++ literals from independent *.xmq sources.

Source of truth: drivers/<name>.xmq. Never edit generated header.
The generator runs during ESPHome component loading and in CI host tests.
"""
from pathlib import Path
import hashlib
import json
import re

_FILENAME = re.compile(r"^[a-z][a-z0-9_]*$")
_NAME = re.compile(r"\bname\s*=\s*([a-z][a-z0-9_]*)\b")
_HEADER = "xmq_driver_sources.h"


def generate_driver_header(component_dir: Path) -> Path:
    component_dir = Path(component_dir)
    source_dir = component_dir / "drivers"
    paths = sorted(source_dir.glob("*.xmq"))
    if not paths:
        raise ValueError("No *.xmq drivers in " + str(source_dir))
    declarations = [
        "#pragma once",
        "// GENERATED from drivers/*.xmq; never modify directly.",
        "// Edit only the individual .xmq file.",
        "#include <cstddef>",
        "#include <cstring>",
        "namespace xmq_runtime {",
    ]
    seen = set()
    for path in paths:
        name = path.stem
        if not _FILENAME.fullmatch(name) or name in seen:
            raise ValueError("Invalid or duplicate XMQ driver filename: " + path.name)
        seen.add(name)
        content = path.read_text(encoding="utf-8")
        declared = _NAME.search(content)
        if declared is None or declared.group(1) != name:
            raise ValueError("XMQ driver name mismatch: " + path.name)
        if "driver {" not in content:
            raise ValueError("Missing XMQ driver block: " + path.name)
        # C++ raw string delimiters must not exceed 16 characters.
        delimiter = "X" + hashlib.sha256(name.encode("utf-8")).hexdigest()[:12]
        if ")" + delimiter + '"' in content:
            raise ValueError("Invalid embedded raw-string delimiter: " + path.name)
        declarations.extend([
            f"inline const char *source_{name}() {{",
            f'  return R"{delimiter}({content}){delimiter}";',
            "}",
        ])
    # Names are embedded in one generated index; no handwritten list to maintain.
    declarations.extend([
        "struct DriverSource { const char *name; const char *source; };",
        "inline const DriverSource *driver_catalog(std::size_t &count) {",
        "  static const DriverSource entries[] = {",
    ])
    for name in sorted(seen):
        declarations.append(f'    {{"{name}", source_{name}()}},')
    declarations.extend([
        "  };",
        "  count = sizeof(entries) / sizeof(entries[0]);",
        "  return entries;",
        "}",
        "inline const char *source_by_name(const char *name) {",
        "  if (name == nullptr) return nullptr;",
        "  std::size_t count = 0;",
        "  const DriverSource *entries = driver_catalog(count);",
        "  for (std::size_t i = 0; i < count; ++i)",
        "    if (std::strcmp(name, entries[i].name) == 0) return entries[i].source;",
        "  return nullptr;",
        "}",
        "struct DriverProfile { const char *name; const char *family; const char *required_numeric; };",
        "}  // namespace xmq_runtime",
    ])
    profiles = json.loads((component_dir / "validated_profiles.json").read_text(encoding="utf-8"))
    if not isinstance(profiles, list) or not (1 <= len(profiles) <= 32):
        raise ValueError("Invalid validated XMQ profiles")
    approved = set()
    declarations.extend([
        "namespace xmq_runtime {",
        "inline const DriverProfile *validated_profile_catalog(std::size_t &count) {",
        "  static const DriverProfile profiles[] = {",
    ])
    for profile in profiles:
        if not isinstance(profile, dict) or set(profile) != {"driver", "family", "required_numeric"}:
            raise ValueError("Invalid validated profile")
        name, family, fields = profile["driver"], profile["family"], profile["required_numeric"]
        if not isinstance(name, str) or name not in seen or name in approved:
            raise ValueError("Approved driver missing/duplicated")
        if family not in ("heat", "water") or not isinstance(fields, list) or not 1 <= len(fields) <= 16:
            raise ValueError("Invalid approved family/fields")
        if any(not isinstance(x, str) or not _FILENAME.fullmatch(x) for x in fields) or len(set(fields)) != len(fields):
            raise ValueError("Invalid approved numeric fields")
        approved.add(name)
        declarations.append(f'    {{"{name}", "{family}", "{",".join(fields)}"}},')
    declarations.extend([
        "  };",
        "  count = sizeof(profiles) / sizeof(profiles[0]);",
        "  return profiles;",
        "}",
        "}  // namespace xmq_runtime",
    ])
    # Transport allowlist is independent of XMQ driver source and publication profiles.
    # This table is not proof of authentication; it admits known clear-form envelopes only.
    signatures = json.loads((component_dir / "transport_signatures.json").read_text(encoding="utf-8"))
    if not isinstance(signatures, list) or not signatures or len(signatures) > 128:
        raise ValueError("Invalid XMQ transport signature list")
    declarations.extend([
        "namespace xmq_runtime {",
        "struct TransportSignature {",
        "  const char *driver; unsigned char version, type, ci, prefix_len, security_mode;",
        "  unsigned char prefix[3];",
        "};",
        "inline const TransportSignature *transport_signature_catalog(std::size_t &count) {",
        "  static const TransportSignature signatures[] = {",
    ])
    # Reject ALL overlapping signatures, not only exact duplicates.
    # A shorter clear-form prefix must never shadow an encrypted_pending one,
    # even for the same approved driver and identical MVT.
    prior_signatures = []
    for item in signatures:
        if not isinstance(item, dict) or set(item) != {"driver", "version", "type", "ci", "prefix", "security"}:
            raise ValueError("Invalid XMQ transport signature")
        name, version, typ, ci, prefix = (
            item["driver"], item["version"], item["type"], item["ci"], item["prefix"])
        security = item["security"]
        if security not in ("clear_form", "encrypted_pending"):
            raise ValueError("Unsupported XMQ security mode")
        if not isinstance(name, str) or name not in approved:
            raise ValueError("Unapproved transport driver")
        if any(type(v) is not int or not (0 <= v <= 255) for v in (version, typ, ci)):
            raise ValueError("Invalid XMQ transport byte")
        if not isinstance(prefix, list) or not 1 <= len(prefix) <= 3 or any(
            type(v) is not int or not (0 <= v <= 255) for v in prefix
        ):
            raise ValueError("Invalid XMQ transport prefix")
        for earlier in prior_signatures:
            old_name, old_version, old_type, old_ci, old_prefix, old_security = earlier
            if (version, typ, ci) != (old_version, old_type, old_ci):
                continue
            common = min(len(prefix), len(old_prefix))
            if prefix[:common] == old_prefix[:common]:
                raise ValueError(
                    "Overlapping XMQ transport signatures: "
                    + old_name + "/" + old_security + " and " + name + "/" + security
                )
        prior_signatures.append((name, version, typ, ci, prefix, security))
        padded = prefix + [0] * (3 - len(prefix))
        declarations.append(
            f'    {{"{name}", {version}, {typ}, {ci}, {len(prefix)}, {0 if security == "clear_form" else 1}, '
            f'{{{padded[0]}, {padded[1]}, {padded[2]}}}}},')
    clear_drivers = {
        name for name, _, _, _, _, security in prior_signatures
        if security == "clear_form"
    }
    missing_clear = approved - clear_drivers
    if missing_clear:
        raise ValueError("Approved XMQ drivers without clear-form transport: "
                         + ", ".join(sorted(missing_clear)))
    declarations.extend([
        "  };",
        "  count = sizeof(signatures) / sizeof(signatures[0]);",
        "  return signatures;",
        "}",
        "inline const char *match_transport_signature(",
        "    unsigned char version, unsigned char type, unsigned char ci,",
        "    const unsigned char *application, std::size_t length) {",
        "  if (application == nullptr) return nullptr;",
        "  std::size_t count = 0;",
        "  const auto *entries = transport_signature_catalog(count);",
        "  const char *match = nullptr;",
        "  for (std::size_t i = 0; i < count; ++i) {",
        "    const auto &sig = entries[i];",
        "    if (sig.security_mode != 0 || sig.version != version || sig.type != type || sig.ci != ci ||",
        "        length < sig.prefix_len ||",
        "        std::memcmp(application, sig.prefix, sig.prefix_len) != 0) continue;",
        "    if (match != nullptr && std::strcmp(match, sig.driver) != 0) return nullptr;",
        "    match = sig.driver;",
        "  }",
        "  return match;",
        "}",
        "}  // namespace xmq_runtime",
    ])
    generated = "\n".join(declarations) + "\n"
    target = component_dir / _HEADER
    if not target.exists() or target.read_text(encoding="utf-8") != generated:
        target.write_text(generated, encoding="utf-8")
    return target


if __name__ == "__main__":
    generate_driver_header(Path(__file__).resolve().parent)
