## Context

See proposal.md for motivation. The canvas currently draws text vertically
centered in each bbox (canvas.py: `_draw_bbox`, using Pango ink extents and
centering by `-text_h/2`). The `Bbox` already stores `baseline` from hOCR
(canvas.py:267; bboxtree.py parses baseline). Tesseract emits `x_ascenders`,
`x_descenders`, `x_size` (and `x_height`/`x_fsize`) when `hocr_font_info=1` is
enabled; these are not parsed/stored. Our controlled test with Tesseract 5.5.0
shows descender words have bbox height extended vs non-descender words on the
same line, confirming the mismatch when centering.
