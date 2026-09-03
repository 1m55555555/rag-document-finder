# Candidate Scoring Rubric

Score candidates from observable PDF evidence. Apply hard requirements before
using the score.

| Dimension | Weight | Evidence |
| --- | ---: | --- |
| Source quality | 25 | Official publisher, vendor, government, university, or standards body |
| Layout match | 25 | Requested screenshots, diagrams, tables, captions, or sparse-text pages are present |
| Visual usefulness | 20 | Images or vector diagrams occupy meaningful page area and are not only logos/icons |
| Procedure continuity | 15 | Numbered steps and related visuals occur in a coherent page sequence |
| Page range | 10 | PDF is close to the requested size |
| Download and parse quality | 5 | Direct PDF downloads and can be inspected without corruption |

## Suggested hard filters

- Reject non-PDF files when the request requires PDFs.
- Reject inaccessible links when a direct download is required.
- Reject documents with no relevant visual evidence when images are required.
- Mark a document as a near match when it violates a soft preference such as
  language or page count.

## Interpretation notes

- A page with low extracted text and high drawing coverage can be visually rich
  even when it has no embedded raster image.
- A PDF can contain an image-rich page whose embedded images are only layers;
  inspect the rendered page before treating each extracted image as a useful
  asset.
- A catalog may have many product photos but little procedural value. Score
  procedure continuity separately from visual usefulness.
