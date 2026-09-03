#!/usr/bin/env python
"""检查 PDF 的版式信号，并可渲染代表性页面供人工复核。"""

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


STEP_PATTERN = re.compile(r"(?:^|\n)\s*(?:\d{1,3}[.)、。]|step\s*\d+|第\s*\d+\s*步)", re.I)
CAPTION_PATTERN = re.compile(r"(?:^|\n)\s*(?:图|表|figure|fig\.?|table)\s*\d+", re.I)
TABLE_CUE_PATTERN = re.compile(
    r"(?:表\s*\d+|table\s*\d+|字段|参数|规格|项目|名称|类型|说明|field|parameter|specification)", re.I
)


def area(rect: Any) -> float:
    return max(0.0, float(rect.width)) * max(0.0, float(rect.height))


def union_area(rectangles: list[Any]) -> float:
    edges = sorted({float(r.x0) for r in rectangles} | {float(r.x1) for r in rectangles})
    total = 0.0
    for left, right in zip(edges, edges[1:]):
        spans = sorted((float(r.y0), float(r.y1)) for r in rectangles if r.x0 < right and r.x1 > left)
        covered = 0.0
        cursor: float | None = None
        for top, bottom in spans:
            if cursor is None:
                cursor = bottom
                covered += max(0.0, bottom - top)
            elif bottom > cursor:
                covered += max(0.0, bottom - max(top, cursor))
                cursor = bottom
        total += max(0.0, right - left) * covered
    return total


def page_report(page: Any, number: int) -> dict[str, Any]:
    text = page.get_text("text").strip()
    page_area = area(page.rect) or 1.0
    image_info = page.get_image_info(xrefs=True)
    image_rects = []
    for item in image_info:
        bbox = item.get("bbox")
        if bbox:
            rect = fitz.Rect(bbox) & page.rect
            if not rect.is_empty:
                image_rects.append(rect)
    image_ratio = min(1.0, union_area(image_rects) / page_area)
    drawing_ratio = min(
        1.0,
        sum(area(item["rect"]) for item in page.get_drawings() if item.get("rect")) / page_area,
    )
    visual_ratio = max(image_ratio, drawing_ratio)
    try:
        detected_tables = len(page.find_tables().tables)
    except Exception:
        detected_tables = 0
    return {
        "page": number,
        "text_chars": len(text),
        "embedded_images": len(image_info),
        "image_area_ratio": round(image_ratio, 4),
        "drawing_area_ratio": round(drawing_ratio, 4),
        "has_numbered_steps": bool(STEP_PATTERN.search(text)),
        "has_caption": bool(CAPTION_PATTERN.search(text)),
        "detected_tables": detected_tables,
        "probable_table": bool(detected_tables or TABLE_CUE_PATTERN.search(text)),
        "image_heavy": visual_ratio >= 0.35,
        "sparse_text_visual": len(text) < 80 and visual_ratio >= 0.35,
    }


def summarize(pages: list[dict[str, Any]]) -> dict[str, Any]:
    selected = lambda key: [item["page"] for item in pages if item[key]]
    return {
        "page_count": len(pages),
        "image_pages": selected("image_heavy"),
        "sparse_text_visual_pages": selected("sparse_text_visual"),
        "procedure_pages": selected("has_numbered_steps"),
        "caption_pages": selected("has_caption"),
        "probable_table_pages": selected("probable_table"),
        "detected_table_pages": [p["page"] for p in pages if p["detected_tables"]],
        "detected_table_count": sum(p["detected_tables"] for p in pages),
        "total_embedded_images": sum(p["embedded_images"] for p in pages),
    }


def representative_pages(pages: list[dict[str, Any]], limit: int) -> list[int]:
    chosen: list[int] = []
    for predicate in (
        lambda p: p["sparse_text_visual"],
        lambda p: p["image_heavy"],
        lambda p: p["detected_tables"] > 0 or p["probable_table"],
        lambda p: p["has_numbered_steps"],
    ):
        for page in pages:
            if predicate(page) and page["page"] not in chosen:
                chosen.append(page["page"])
                break
        if len(chosen) >= limit:
            return chosen[:limit]
    for number in (1, max(1, (len(pages) + 1) // 2), len(pages)):
        if number not in chosen:
            chosen.append(number)
        if len(chosen) >= limit:
            break
    return chosen[:limit]


def render_pages(pdf: Path, page_numbers: list[int], output_dir: Path) -> list[dict[str, Any]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    document = fitz.open(pdf)
    rendered = []
    try:
        for number in page_numbers:
            output = output_dir / f"page-{number:04d}.png"
            pixmap = document.load_page(number - 1).get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
            pixmap.save(output)
            rendered.append({"page": number, "path": str(output.resolve())})
    finally:
        document.close()
    return rendered


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--render-dir", type=Path)
    parser.add_argument("--render-samples", type=int, default=3)
    args = parser.parse_args()
    if not args.pdf.is_file():
        parser.error(f"PDF not found: {args.pdf}")
    try:
        document = fitz.open(args.pdf)
        try:
            pages = [page_report(page, i + 1) for i, page in enumerate(document)]
        finally:
            document.close()
    except Exception as exc:
        print(json.dumps({"error": f"open_failed:{type(exc).__name__}"}), file=sys.stderr)
        return 2
    report: dict[str, Any] = {"file": str(args.pdf.resolve()), "summary": summarize(pages), "pages": pages}
    if args.render_dir:
        report["rendered_samples"] = render_pages(
            args.pdf, representative_pages(pages, args.render_samples), args.render_dir
        )
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
