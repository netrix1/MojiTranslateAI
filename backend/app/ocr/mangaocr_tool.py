from __future__ import annotations

from typing import Dict, Any, Optional, List

from PIL import Image
from manga_ocr import MangaOcr

from app.ocr.detect_regions import detect_regions

# Singleton para evitar recarregar o modelo a cada request
_MANGA_OCR: Optional[MangaOcr] = None


def _get_ocr() -> MangaOcr:
    global _MANGA_OCR
    if _MANGA_OCR is None:
        _MANGA_OCR = MangaOcr()
    return _MANGA_OCR


def run_ocr_mangaocr(
    image_path: str,
    chapter_id: str = "001",
    page_number: int = 1,
    image_filename: str = "001.jpg",
    regions: Optional[Dict] = None,
) -> Dict[str, Any]:
    """
    OCR real (v2):
    - Uses provided regions (if any) or runs heuristic detection
    - Executa MangaOCR em cada crop
    """
    ocr = _get_ocr()

    img = Image.open(image_path).convert("RGB")
    width, height = img.size

    bboxes: List[List[int]] = []

    # 1) Use existing regions if provided (Strict Mode)
    if regions:
        print(f"[MangaOCR] Regions provided. Looking for page_number={page_number} (type {type(page_number)})")
        found_page = False
        if "pages" in regions and isinstance(regions["pages"], list):
            for p in regions["pages"]:
                 # Weak comparison to handle string/int mismatch
                 p_num = p.get("page_number")
                 if str(p_num) == str(page_number):
                      found_page = True
                      r_list = p.get("regions", [])
                      print(f"[MangaOCR] Found page {page_number}. Extracting {len(r_list)} regions.")
                      for r in r_list:
                           if "bbox" in r:
                                bboxes.append(r["bbox"])
                      break
        
        if not found_page:
            print(f"[MangaOCR] WARNING: Regions provided but page {page_number} not found in structure.")

    # 2) Fallback to detection if NO regions provided (First run)
    if not regions and not bboxes:
        print("[MangaOCR] No regions provided (auto-mode). Running detection...")
        try:
            bboxes = detect_regions(image_path)
        except Exception as e:
            print(f"[MangaOCR] Detection failed: {e}")
            bboxes = []
            
    print(f"[MangaOCR] Final processing: {len(bboxes)} bboxes. Image size: {width}x{height}")

    if not bboxes:
        if regions:
             # Strict mode: If user provided regions and we found none (or page empty), we respect that.
             # Returning empty list might break pipeline if it expects something?
             # But usually pipeline handles empty blocks fine.
             print("[MangaOCR] 0 bboxes from provided regions. Returning empty result.")
             pass
        else:
             print("[MangaOCR] No bboxes found/provided. Fallback to page-level.")
             bboxes = [[0, 0, width, height]]

    blocks: List[Dict[str, Any]] = []
    idx = 1
    for (x1, y1, x2, y2) in bboxes:
        # Validate coords
        x1, y1 = max(0, int(x1)), max(0, int(y1))
        x2, y2 = min(width, int(x2)), min(height, int(y2))
        
        if x2 <= x1 or y2 <= y1:
            print(f"[MangaOCR] Invalid bbox detected: {x1},{y1},{x2},{y2} - skipping")
            continue

        crop = img.crop((x1, y1, x2, y2))
        text = (ocr(crop) or "").strip()
        
        print(f"[MangaOCR] Block {idx} ({x1},{y1},{x2},{y2}): '{text}'")
        
        if not text:
             # Keep empty block if it was explicitly a region? 
             # Or maybe it's just noise. 
             # If user provided region, we should probably keep it even if empty, so they can edit.
             # PREVIOUS Logic: continued if not text.
             # CHANGE: If explicit regions were used, we might want to keep it?
             # For now, let's keep the logging and see.
             pass

        if not text:
            # If explicit regions were provided, keep the block so user can edit it.
            if regions:
                print(f"[MangaOCR] Keeping empty block {idx} because regions were explicit.")
                pass
            else:
                # In auto-detection mode, skip empty noise
                continue

        blocks.append(
            {
                "block_id": f"t{idx}",
                "original_text": text,
                "bbox": [int(x1), int(y1), int(x2), int(y2)],
                "is_speech": True,
                "is_sfx": False,
                "shape_hint": "unknown",
                "max_characters": 40,
                "max_lines": 2,
                "notes": "mangaocr_crop_v2"
                if (x1, y1, x2, y2) != (0, 0, width, height)
                else "mangaocr_pagelevel_v2",
                "group_id": None,
                "reading_order": None,
                "block_type": "unknown",
            }
        )
        idx += 1

    # Fallback extremo: se tudo ficar vazio, cria 1 bloco vazio (para manter schema)
    if not blocks:
        blocks = [
            {
                "block_id": "t1",
                "original_text": "",
                "bbox": [0, 0, width, height],
                "is_speech": True,
                "is_sfx": False,
                "shape_hint": "unknown",
                "max_characters": 40,
                "max_lines": 2,
                "notes": "mangaocr_empty_fallback_v2",
                "group_id": None,
                "reading_order": None,
                "block_type": "unknown",
            }
        ]

    return {
        "chapter_id": chapter_id,
        "pages": [
            {
                "page_number": page_number,
                "image_file": image_filename,
                "blocks": blocks,
            }
        ],
    }
