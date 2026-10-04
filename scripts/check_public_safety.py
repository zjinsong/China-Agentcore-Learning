"""Small pre-publish guard; not a replacement for a full secret scanner."""
from pathlib import Path
import re
import sys

patterns = {
    "AWS access key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "account id": re.compile(r"\b\d{12}\b"),
    "IPv4 address": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
}
ignored = {".git", ".venv", "node_modules", "artifacts", "reports"}
hits = []
for path in Path(".").rglob("*"):
    if not path.is_file() or any(part in ignored for part in path.parts):
        continue
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        continue
    for label, pattern in patterns.items():
        match = pattern.search(text)
        if match and not (label == "IPv4 address" and match.group() in {"127.0.0.1", "0.0.0.0"}):
            hits.append(f"{label}: {path}")
if hits:
    print("Potential public data detected:\n" + "\n".join(hits))
    sys.exit(1)
print("Public safety check passed")
