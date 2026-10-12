"""Fetch the public references the ground-truth tests read, and record them in MANIFEST.json.

The copies stay on the maintainer's machine (git ignores them); only the manifest with
each URL, size and SHA-256 is tracked. Run from the repository root:

    python scripts/fetch_sources.py
"""

from __future__ import annotations

import datetime
import hashlib
import json
import urllib.request
from pathlib import Path

SOURCES = {
    "ni-labview-timestamp-overview.html": (
        "https://www.ni.com/en/support/documentation/supplemental/08/"
        "labview-timestamp-overview.html"
    ),
    "ni-tdms-file-format-internal-structure.html": (
        "https://www.ni.com/en/support/documentation/supplemental/07/"
        "tdms-file-format-internal-structure.html"
    ),
    "nptdms-types.py": "https://raw.githubusercontent.com/adamreeve/npTDMS/master/nptdms/types.py",
    "nptdms-timestamp.py": (
        "https://raw.githubusercontent.com/adamreeve/npTDMS/master/nptdms/timestamp.py"
    ),
    "nptdms-tdms.py": "https://raw.githubusercontent.com/adamreeve/npTDMS/master/nptdms/tdms.py",
}

FOLDER = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "sources"


def main() -> None:
    FOLDER.mkdir(parents=True, exist_ok=True)
    today = datetime.date.today().isoformat()
    entries = []
    for name, url in SOURCES.items():
        request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(request, timeout=60) as response:
            body = response.read()
        (FOLDER / name).write_bytes(body)
        digest = hashlib.sha256(body).hexdigest()
        entries.append(
            {"file": name, "url": url, "fetched": today, "size": len(body), "sha256": digest}
        )
    manifest = {"note": "public references fetched for the ground-truth tests", "files": entries}
    text = json.dumps(manifest, indent=2) + "\n"
    (FOLDER / "MANIFEST.json").write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
