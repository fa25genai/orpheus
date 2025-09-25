import fitz  # PyMuPDF
import base64
from io import BytesIO
from PIL import Image, ImageStat

EXT_TO_MIME = {
    "png":  "image/png",
    "jpg":  "image/jpeg",
    "jpeg": "image/jpeg",
    "tif":  "image/tiff",
    "tiff": "image/tiff",
    "gif":  "image/gif",
    "bmp":  "image/bmp",
    "webp": "image/webp",
    "jpx":  "image/jpx",
    "jp2":  "image/jp2",
}

def is_black_square(img_bytes, darkness_threshold=30, variance_threshold=15):
    """Heuristik zum Erkennen von schwarzen Kästchen (z. B. Codeblock-Placeholder)."""
    image = Image.open(BytesIO(img_bytes)).convert("L")
    stat = ImageStat.Stat(image)
    return stat.mean[0] < darkness_threshold and stat.stddev[0] < variance_threshold

def extract_images_grouped(pdf_path):
    """
    Rückgabe: List[List[dict]]
      - äußere Liste = Seiten
      - innere Liste = Bilder auf der Seite
      - jedes Bild: { "data": base64, "mime_type": "image/..." }
    """
    pdf = fitz.open(pdf_path)
    result = []

    print(f"Öffne PDF: {pdf_path} | Seiten: {len(pdf)}")

    for page_number, page in enumerate(pdf, start=1):
        print(f"\n[Seite {page_number}] Verarbeitung gestartet...")
        page_items = []
        images = page.get_images(full=True)
        print(f"  Gefundene Bilder: {len(images)}")

        for img_index, (xref, smask, *_) in enumerate(images, start=1):
            if smask:  # Soft-Masken überspringen
                print(f"    [Bild {img_index}] Soft-Maske erkannt → übersprungen")
                continue

            info = pdf.extract_image(xref)
            img_bytes = info["image"]

            if is_black_square(img_bytes):
                print(f"    [Bild {img_index}] Schwarzes Kästchen erkannt → übersprungen")
                continue

            ext = (info.get("ext") or "").lower()
            mime = EXT_TO_MIME.get(ext, "application/octet-stream")

            print(f"    [Bild {img_index}] extrahiert (MIME: {mime}, Größe: {len(img_bytes)} Bytes)")

            page_items.append({
                "data": base64.b64encode(img_bytes).decode("utf-8"),
                "mime_type": mime
            })

        if not page_items:
            print(f"  Keine gültigen Bilder auf Seite {page_number}")

        result.append(page_items)

    pdf.close()
    print(f"\nExtraktion abgeschlossen. Seiten: {len(result)} | Bilder insgesamt: {sum(len(p) for p in result)}")
    return result
