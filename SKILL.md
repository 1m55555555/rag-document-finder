---
name: rag-document-finder
description: "Discover and verify public PDFs for RAG evaluation when users need documents with specific layouts, images, tables, procedures, or sparse-text pages."
---

# RAG Document Finder

Find documents that are genuinely useful for RAG testing, rather than merely
returning search results with similar titles. Use this skill when the user asks
for public manuals, SOPs, installation guides, operation guides, or documents
with a required combination of text, images, tables, diagrams, and steps.

## Define success

Turn the request into a compact target profile before searching. Capture only
constraints that affect suitability:

- document type and domain;
- language and approximate page range;
- required layout evidence, such as numbered procedures, screenshots, tables,
  figure captions, image-heavy pages, or text-free pages;
- source requirements, especially whether official sources and direct PDF links
  are required.

Treat unspecified constraints as preferences, not hard filters. Do not infer a
specific product, vendor, or document family from an example document.

## Search and shortlist

Search with multiple query families: the requested language, English technical
terms where useful, and credible-source constraints such as manufacturer,
government, university, standards body, or official documentation domains.

Prefer direct downloadable PDFs and record the exact PDF URL. A search-result
snippet or viewer page is not evidence that the PDF has the requested layout.
Do not present a marketing brochure, catalog, or generic overview as a
procedure manual unless the PDF inspection supports that classification.

## Verify the actual PDF

For each serious candidate, download it only after the user has allowed network
access or asked for the document. Run the UTF-8 checker (the original
`inspect_pdf.py` remains as a legacy entry point):

```powershell
python scripts/inspect_pdf_v2.py <pdf-path> --output <report.json> `
  --render-dir <rendered-pages> --render-samples 3
```

The report measures page count, extracted-text density, raster images, vector
drawings, image coverage, numbered-step cues, captions, and probable table
pages. Read [references/scoring-rubric.md](references/scoring-rubric.md) when
ranking candidates.

Open the selected PNGs and visually confirm the claimed screenshots, diagrams,
tables, or sparse-text pages. Rendering is a spot-check, not automatic proof.
The selector prefers sparse visual pages, image-heavy pages, table-like pages,
and procedure pages, in that order.

Record the verified result in a UTF-8 candidate manifest:

```powershell
python scripts/record_candidate.py <pdf-path> `
  --manifest <candidate_manifest.json> `
  --source-url <direct-pdf-url> `
  --inspection-report <report.json> `
  --title "..." --publisher "..." --language zh `
  --score 86 --status verified
```

`candidate_manifest.json` records the source URL, local file hash, inspection
summary, rendered samples, score, status, rejection reasons, and notes. It is
an audit record only; it does not upload or ingest documents.

Do not claim a document is image-only solely because `get_images()` returns
images. Vector artwork and scanned full-page renders require interpreting the
page-level report. Do not claim a table exists just because text is aligned in
columns; report it as a probable table unless the structure is visible.

## Deliverable

Return a short ranked list. For each candidate include:

- title, publisher/source, direct PDF link, language, and page count;
- observed layout evidence and page ranges;
- score and the reason it matches the requested RAG test;
- limitations or uncertainty.

Separate confirmed findings from inference. If no candidate meets the hard
requirements, say so and return the closest alternatives with the mismatches.

## Boundaries

- Do not upload, ingest, or delete documents unless asked separately.
- Do not bypass paywalls, login walls, robots restrictions, or access controls.
- Stop after a bounded shortlist, normally three to five verified candidates.
- Use browser automation only when a real browser session is necessary to reach
  an already accessible page; otherwise use ordinary web search and direct PDFs.
