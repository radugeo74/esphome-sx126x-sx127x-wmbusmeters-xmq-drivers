"""Generate XMQ C++ literals from independent *.xmq sources.

Source of truth: drivers/<name>.xmq. Never edit generated header.
The generator runs during ESPHome component loading and in CI host tests.
"""
from pathlib import Path
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
        delimiter = "XMQ_" + name.upper()
        if ")" + delimiter + '"' in content:
            raise ValueError("Invalid embedded raw-string delimiter: " + path.name)
        declarations.extend([
            f"inline const char *source_{name}() {{",
            f'  return R"{delimiter}({content}){delimiter}";',
            "}",
        ])
    declarations.append("}  // namespace xmq_runtime")
    generated = "\n".join(declarations) + "\n"
    target = component_dir / _HEADER
    if not target.exists() or target.read_text(encoding="utf-8") != generated:
        target.write_text(generated, encoding="utf-8")
    return target


if __name__ == "__main__":
    generate_driver_header(Path(__file__).resolve().parent)
