"""Acquire explicitly pinned official documentation; no scraping or retrieval scoring."""
from __future__ import annotations

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
REVISION = "60403a5409ff2c3f3b07dd2ca91a7a3e096839c7"  # CPython v3.13.0 tag target
BUNDLES = {
    "asyncio": ["asyncio-task", "asyncio-sync"],
    "processes": ["subprocess", "shlex"],
    "executors": ["concurrent.futures", "queue"],
    "multiprocessing": ["multiprocessing", "multiprocessing.shared_memory"],
    "logging": ["logging", "logging.config"],
    "filesystem": ["pathlib", "shutil"],
    "configuration": ["argparse", "configparser"],
    "persistence": ["pickle", "shelve"],
    "archives": ["tarfile", "zipfile"],
    "networking": ["socket", "ssl"],
    "http": ["urllib.request", "http.client"],
    "database": ["sqlite3", "contextlib"],
}


def acquire(item: tuple[str, str]) -> dict[str, object]:
    family, name = item
    upstream = f"Doc/library/{name}.rst"
    url = f"https://raw.githubusercontent.com/python/cpython/{REVISION}/{upstream}"
    path = ROOT / f"evals/phase10b_sources/cpython/{upstream}"
    if path.exists():
        raise FileExistsError(path)
    with urlopen(url, timeout=60) as response:
        content = response.read()
    content.decode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(content)
    return {"source_id": name, "family": f"python-{family}",
        "source_path": f"cpython/{REVISION}/{upstream}",
        "snapshot": str(path.relative_to(ROOT)), "url": url,
        "revision": REVISION, "version": "CPython 3.13.0", "source_type": "official_documentation",
        "sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content),
        "license": "PSF License Version 2; source LICENSE retained alongside snapshots",
        "permission_basis": "Official publicly distributed Python documentation under PSF license",
        "retrieved_at": datetime.now(UTC).isoformat(), "transformations": "none"}


def main() -> None:
    target = ROOT / "evals/phase10b_external_sources.json"
    if target.exists():
        raise FileExistsError(target)
    items = [(family, name) for family, names in BUNDLES.items() for name in names]
    with ThreadPoolExecutor(max_workers=4) as executor:
        sources = list(executor.map(acquire, items))
    url = f"https://raw.githubusercontent.com/python/cpython/{REVISION}/LICENSE"
    with urlopen(url, timeout=60) as response:
        license_bytes = response.read()
    license_path = ROOT / "evals/phase10b_sources/cpython/LICENSE"
    with license_path.open("xb") as stream:
        stream.write(license_bytes)
    value = {"tag": "v3.13.0", "commit": REVISION, "sources": sources,
        "license": {"url": url, "snapshot": str(license_path.relative_to(ROOT)),
                    "sha256": hashlib.sha256(license_bytes).hexdigest()}}
    with target.open("x") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")
    print(f"Pinned {len(sources)} official documentation files and LICENSE")


if __name__ == "__main__":
    main()
