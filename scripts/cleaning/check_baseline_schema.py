#!/usr/bin/env python3
"""Read-only checksum and report checks for local coursework data."""
import hashlib
import json
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'project.json').is_file())
PROCESSED = ROOT / "data" / "processed"


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    report = json.loads((PROCESSED / "quality_report.json").read_text(encoding="utf-8"))
    if report.get("api_calls_made") != 0:
        raise SystemExit("Quality report does not confirm zero API calls.")
    if not report.get("output_validation", {}).get("passed"):
        raise SystemExit("Cleaned outputs have no passing read-back validation.")

    checked = 0
    for line in (PROCESSED / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
        expected, relative = line.split("  ", 1)
        path = PROCESSED / relative
        if not path.is_file() or sha256(path) != expected:
            raise SystemExit(f"Output checksum mismatch: {relative}")
        checked += 1

    reasoning = report["reasoning"]
    reasoning_archive = ROOT / "data" / "raw" / "reasoning" / "responses_source.zip"
    if sha256(reasoning_archive) != reasoning["source_expected_sha256"]:
        raise SystemExit("reasoning source archive checksum mismatch.")

    document_qa = report["document_qa"]
    checksums = json.loads((ROOT / "data" / "raw" / "document_qa" / "CHECKSUMS.json").read_text(encoding="utf-8"))
    for relative, details in document_qa["verified_input_hashes"].items():
        expected = checksums[relative]["sha256"]
        path = ROOT / "data" / "raw" / "document_qa" / relative
        if expected != details["sha256"] or sha256(path) != expected:
            raise SystemExit(f"document_qa source input checksum mismatch: {relative}")

    print(f"OK: {checked} processed-file checksums and both source packages verified.")


if __name__ == "__main__":
    main()
