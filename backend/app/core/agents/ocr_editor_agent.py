from __future__ import annotations
from app.schemas import OCRDocument

def ocr_editor_agent(ocr_grouped: dict):
    # Placeholder (no-op). Futuro: gerar overrides reais via IA.
    doc = OCRDocument(**ocr_grouped)
    overrides = []
    return doc.model_dump(), overrides
