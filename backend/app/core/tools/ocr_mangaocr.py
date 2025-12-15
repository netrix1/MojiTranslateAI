from __future__ import annotations
from pathlib import Path
from typing import List, Tuple
from app.schemas import OCRDocument, OCRPage, OCRBlock
import numpy as np

def _detect_text_regions(img_rgb: np.ndarray, max_blocks: int) -> List[Tuple[int,int,int,int]]:
    import cv2
    gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)
    thr = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 31, 10)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9,9))
    dil = cv2.dilate(thr, kernel, iterations=1)
    contours, _ = cv2.findContours(dil, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    h, w = gray.shape[:2]
    boxes = []
    for c in contours:
        x, y, ww, hh = cv2.boundingRect(c)
        area = ww * hh
        if area < 800:
            continue
        if ww < 20 or hh < 20:
            continue
        if ww > w*0.95 and hh > h*0.95:
            continue
        pad = 4
        x1 = max(0, x - pad)
        y1 = max(0, y - pad)
        x2 = min(w, x + ww + pad)
        y2 = min(h, y + hh + pad)
        boxes.append((x1,y1,x2,y2))

    boxes.sort(key=lambda b: (-(b[0]+b[2])/2, (b[1]+b[3])/2))
    return boxes[:max_blocks]

def run_ocr_mangaocr(image_path: Path, page_number: int, max_blocks: int = 40) -> dict:
    try:
        from PIL import Image
        from manga_ocr import MangaOcr
    except Exception as e:
        raise RuntimeError(
            "MangaOCR não está instalado. Instale PyTorch primeiro e depois rode: "
            "pip install -r requirements-ocr-mangaocr.txt"
        ) from e

    ocr = MangaOcr()
    img = Image.open(image_path).convert("RGB")
    img_np = np.array(img)

    boxes = _detect_text_regions(img_np, max_blocks=max_blocks)
    blocks = []
    for i, (x1,y1,x2,y2) in enumerate(boxes, start=1):
        crop = img.crop((x1,y1,x2,y2))
        try:
            text = ocr(crop)
        except Exception:
            text = ""
        ww = x2 - x1
        hh = y2 - y1
        shape_hint = "vertical" if hh >= ww*1.2 else "horizontal"
        blocks.append(OCRBlock(
            block_id=f"t{i}",
            original_text=(text or "").strip(),
            bbox=[int(x1),int(y1),int(x2),int(y2)],
            is_speech=True,
            is_sfx=False,
            shape_hint=shape_hint,
            max_characters=60 if shape_hint=="horizontal" else 20,
            max_lines=4 if shape_hint=="horizontal" else 8,
            notes="mangaocr+heuristic-detect (baseline)",
            block_type="unknown"
        ))

    if not blocks:
        text = ocr(img)
        blocks = [OCRBlock(
            block_id="t1",
            original_text=(text or "").strip(),
            bbox=[0,0,img.width,img.height],
            is_speech=True,
            is_sfx=False,
            shape_hint="unknown",
            max_characters=999,
            max_lines=999,
            notes="mangaocr full-page fallback",
            block_type="unknown"
        )]

    doc = OCRDocument(
        chapter_id="001",
        pages=[OCRPage(page_number=page_number, image_file=image_path.name, blocks=blocks)]
    )
    return doc.model_dump()
