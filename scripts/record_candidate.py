#!/usr/bin/env python
"""将已检查的 PDF 候选写入候选清单。"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path, default: dict) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--inspection-report", type=Path)
    parser.add_argument("--title", default="")
    parser.add_argument("--publisher", default="")
    parser.add_argument("--language", default="")
    parser.add_argument("--score", type=float)
    parser.add_argument("--status", choices=("pending", "verified", "near_match", "rejected"), default="pending")
    parser.add_argument("--reason", action="append", default=[])
    parser.add_argument("--notes", default="")
    args = parser.parse_args()
    if not args.pdf.is_file():
        parser.error(f"PDF not found: {args.pdf}")
    digest = file_hash(args.pdf)
    manifest = read_json(args.manifest, {"schema_version": 1, "updated_at": now(), "candidates": []})
    candidates = manifest.setdefault("candidates", [])
    candidate = next((item for item in candidates if item.get("sha256") == digest or item.get("source_url") == args.source_url), None)
    if candidate is None:
        candidate = {"id": f"sha256:{digest[:16]}", "created_at": now()}
        candidates.append(candidate)
    candidate.update({
        "title": args.title,
        "publisher": args.publisher,
        "language": args.language,
        "source_url": args.source_url,
        "local_file": str(args.pdf.resolve()),
        "sha256": digest,
        "inspected_at": now(),
        "status": args.status,
        "rejection_reasons": args.reason,
        "notes": args.notes,
    })
    if args.score is not None:
        candidate["score"] = args.score
    if args.inspection_report:
        report = read_json(args.inspection_report, {})
        candidate["inspection_report"] = str(args.inspection_report.resolve())
        candidate["inspection_summary"] = report.get("summary", {})
        candidate["rendered_samples"] = report.get("rendered_samples", [])
    manifest["updated_at"] = now()
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(candidate, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
