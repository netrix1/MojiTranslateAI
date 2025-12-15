from pathlib import Path
import traceback

from app.core.tools.ocr_stub import run_ocr_stub
# from app.ocr.mangaocr_tool import run_ocr_mangaocr
from app.ocr.gpt_vision_tool import run_ocr_gpt_vision


def run_ocr(page_number: int, image_path: Path, chapter_id: str = "001", regions: dict = None) -> dict:
    """
    OCR Router:
    - default: GPT-4 Vision -> Real OCR
    - fallback: stub (if GPT fails)
    """

    # 1) File check
    if not image_path.exists():
        print(f"[OCR_ROUTER] ERROR: image not found at: {image_path}")
        return run_ocr_stub(page_number=page_number, image_filename=image_path.name)

    try:
        # 2) Real OCR (GPT Vision)
        return run_ocr_gpt_vision(
            image_path=str(image_path),
            chapter_id=chapter_id,
            page_number=page_number,
            image_filename=image_path.name,
            regions=regions,
        )
    except Exception:
        # 3) Log error + fallback
        print("[OCR_ROUTER] GPT Vision failed, using OCR_STUB. Full traceback:")
        traceback.print_exc()
        return run_ocr_stub(page_number=page_number, image_filename=image_path.name)

