from pathlib import Path
import traceback

from app.core.tools.ocr_stub import run_ocr_stub
from app.ocr.mangaocr_tool import run_ocr_mangaocr


def run_ocr(page_number: int, image_path: Path, chapter_id: str = "001", regions: dict = None) -> dict:
    """
    OCR Router:
    - padrão: MangaOCR (japonês) -> OCR real
    - fallback: stub (se MangaOCR falhar por qualquer motivo)
    """

    # 1) Verificação de arquivo (evita "falha silenciosa")
    if not image_path.exists():
        print(f"[OCR_ROUTER] ERRO: imagem não encontrada em: {image_path}")
        return run_ocr_stub(page_number=page_number, image_filename=image_path.name)

    try:
        # 2) OCR real
        return run_ocr_mangaocr(
            image_path=str(image_path),
            chapter_id=chapter_id,
            page_number=page_number,
            image_filename=image_path.name,
            regions=regions,
        )
    except Exception:
        # 3) Log do erro real + fallback
        print("[OCR_ROUTER] MangaOCR falhou, usando OCR_STUB. Traceback completo:")
        traceback.print_exc()
        return run_ocr_stub(page_number=page_number, image_filename=image_path.name)

