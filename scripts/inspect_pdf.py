#!/usr/bin/env python
"""Inspect observable PDF layout signals for RAG test-document selection."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

try:
    import fitz
except ImportError as exc:
    raise SystemExit("PyMuPDF is required: pip install pymupdf") from exc


STEP_PATTERN = re.compile(
    r"(?:^|\n)\s*(?:\d{1,3}[.)、]|step\s*\d+|第\s*\d+\s*步)", re.IGNORECASE
)
CAPTION_PATTERN = re.compile(r"(?:^|\n)\s*(?:图|表|figure|table)\s*\d", re.IGNORECASE)
TABLE_CUE_PATTERN = re.compile(r"(?:表\s*\d|table\s*\d|字段|field|参数|parameter)", re.IGNORECASE)


def rect_area(rect: Any) -> float:
    return max(0.0, float(rect.width)) * max(0.0, float(rect.height))


def union_area(rectangles: list[Any]) -> float:
    """Return the covered area of overlapping axis-aligned rectangles."""
    edges = sorted({float(rect.x0) for rect in rectangles} | {float(rect.x1) for rect in rectangles})
    total = 0.0
    for left, right in zip(edges, edges[1:]):
        if right <= left:
            continue
        spans = sorted(
            (float(rect.y0), float(rect.y1))
            for rect in rectangles
            if float(rect.x0) < right and float(rect.x1) > left
        )
        covered = 0.0
        cursor: float | None = None
        for top, bottom in spans:
            if cursor is None:
                cursor = bottom
                covered += max(0.0, bottom - top)
            elif bottom > cursor:
                covered += max(0.0, bottom - max(top, cursor))
                cursor = bottom
        total += (right - left) * covered
    return total


def page_report(page: Any, page_number: int) -> dict[str, Any]:
    text = page.get_text("text").strip()
    page_area = rect_area(page.rect) or 1.0
    image_info = page.get_image_info(xrefs=True)
    image_rectangles = []
    for item in image_info:
        bbox = item.get("bbox")
        if not bbox:
            continue
        clipped = fitz.Rect(bbox) & page.rect
        if not clipped.is_empty:
            image_rectangles.append(clipped)
    image_area = union_area(image_rectangles)
    drawing_area = sum(rect_area(item["rect"]) for item in page.get_drawings() if item.get("rect"))
    image_ratio = min(1.0, image_area / page_area)
    drawing_ratio = min(1.0, drawing_area / page_area)
    sparse_text = len(text) < 80
    visual_ratio = max(image_ratio, drawing_ratio)
    try:
        detected_tables = len(page.find_tables().tables)
    except Exception:
        detected_tables = 0
    return {
        "page": page_number,
        "text_chars": len(text),
        "embedded_images": len(image_info),
        "image_area_ratio": round(image_ratio, 4),
        "drawing_area_ratio": round(drawing_ratio, 4),
        "has_numbered_steps": bool(STEP_PATTERN.search(text)),
        "has_caption": bool(CAPTION_PATTERN.search(text)),
        "detected_tables": detected_tables,
        "probable_table": bool(detected_tables or TABLE_CUE_PATTERN.search(text)),
        "image_heavy": visual_ratio >= 0.35,
        "sparse_text_visual": sparse_text and visual_ratio >= 0.35,
    }


def summarize(pages: list[dict[str, Any]]) -> dict[str, Any]:
    def selected(name: str) -> list[int]:
        return [item["page"] for item in pages if item[name]]

    return {
        "page_count": len(pages),
        "image_pages": selected("image_heavy"),
        "sparse_text_visual_pages": selected("sparse_text_visual"),
        "procedure_pages": selected("has_numbered_steps"),
        "caption_pages": selected("has_caption"),
        "probable_table_pages": selected("probable_table"),
        "detected_table_pages": [item["page"] for item in pages if item["detected_tables"]],
        "detected_table_count": sum(item["detected_tables"] for item in pages),
        "total_embedded_images": sum(item["embedded_images"] for item in pages),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--output", type=Path, help="Optional JSON report path")
    args = parser.parse_args()
    if not args.pdf.is_file():
        parser.error(f"PDF not found: {args.pdf}")

    try:
        document = fitz.open(args.pdf)
    except Exception as exc:
        print(json.dumps({"error": f"open_failed:{type(exc).__name__}"}), file=sys.stderr)
        return 2

    try:
        pages = [page_report(page, index + 1) for index, page in enumerate(document)]
    finally:
        document.close()
    report = {
        "file": str(args.pdf.resolve()),
        "summary": summarize(pages),
        "pages": pages,
    }
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
