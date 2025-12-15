from __future__ import annotations
from app.schemas import OCRDocument, OCRPage, OCRBlock

def run_ocr_stub(page_number: int, image_filename: str) -> dict:
    doc = OCRDocument(
        chapter_id="001",
        pages=[OCRPage(
            page_number=page_number,
            image_file=image_filename,
            blocks=[OCRBlock(
                block_id="t1",
                original_text="(OCR_STUB)",
                bbox=[100,100,300,300],
                is_speech=True,
                is_sfx=False,
                shape_hint="unknown",
                max_characters=40,
                max_lines=2,
                notes="placeholder block",
            )],
        )]
    )
    return doc.model_dump()
