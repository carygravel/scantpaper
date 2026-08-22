## Why

Importing a large TIFF archive (e.g. 250 uncompressed 200 dpi grayscale pages)
takes hours because every page is re-encoded twice: once as a PNG blob for the
database and once more as a full-size PNG just to make a 100 px thumbnail.
Saving those pages as a PDF is then equally slow, because img2pdf cannot embed
uncompressed 8-bit grayscale TIFFs natively and re-encodes them at full PNG-encode
cost. Storing the raw TIFF instead would only right-shift that encoding cost into
img2pdf, so the fix is to store an intermediate format that img2pdf can embed
without re-encoding, chosen per image mode.

## What Changes

- On import, store a compact intermediate blob instead of always re-encoding to PNG:
  - Continuous-tone pages (grayscale/RGB) are stored as JPEG (quality ~92), which img2pdf embeds natively at near-zero cost.
  - Bilevel (1-bit) pages are stored losslessly as PNG, preserving the lossless path for DjVu (cjb2) and bilevel PDFs.
  - If the imported file is already a compact format (JPEG or PNG), store the original bytes as-is with no re-encode.
- Generate thumbnails from a downscaled image before encoding, so the second full-size encode is eliminated.
- When saving as PDF, embed the stored bytes directly (img2pdf passthrough) when no downsampling or compression options require a re-encode.
- The `image` table blob becomes mixed-format (JPEG/PNG); no schema change is needed because all consumers already auto-detect format from the blob header (`Image.open`), and img2pdf auto-detects its input.

## Capabilities

### New Capabilities
- `image-storage-format`: Governs the format in which full-size page images are stored in the database — which formats are used for which image modes, how thumbnails are produced, and when the stored format is passed through unchanged when saving a PDF.

### Modified Capabilities
- `save-progress-reporting`: The PDF save path now has a new possible stage (embedding stored images directly). Per-page progress reporting is unchanged, but the save may skip the PNG re-encode stage for stored JPEG images.

## Impact

- `scantpaper/page.py` — `to_bytes()` (PNG-only today), `get_pixbuf_at_scale()` (full-size PNG for thumbnails), `write_image_for_pdf()` (stored-bytes passthrough).
- `scantpaper/docthread.py` — `_insert_image()` (choose/store the compact blob), `_bytes_to_pixbuf`/thumb generation.
- `scantpaper/importthread.py` — capture original file bytes at import time.
- `scantpaper/savethread.py` — `write_image_for_pdf`/`do_save_pdf` to embed stored bytes without re-encode.
- Database blobs become mixed-format; existing sessions store PNG and remain fully readable.
- Quality: JPEG q92 measures ~39.7 dB PSNR / SSIM 0.990 vs the original TIFF; bilevel pages stay lossless.
- OCR speed is not addressed here (separate change for feeding pixels directly to tesserocr and skipping the byte-compare re-encode).
