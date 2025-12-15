from __future__ import annotations

import os
import tempfile
from typing import Dict, Any, Optional, List
from pathlib import Path

from PIL import Image
from app.ocr.detect_regions import detect_regions
from app.core.llm_client import call_vision_llm

def run_ocr_gpt_vision(
    image_path: str,
    chapter_id: str = "001",
    page_number: int = 1,
    image_filename: str = "001.jpg",
    regions: Optional[Dict] = None,
) -> Dict[str, Any]:
    """
    GPT-4 Vision OCR:
    - Uses provided regions (if any) or runs heuristic detection
    - Crops each region and sends to GPT-4 Vision for transcription
    """
    
    img = Image.open(image_path).convert("RGB")
    width, height = img.size

    bboxes: List[List[int]] = []

    # 1) Use existing regions if provided
    if regions:
        print(f"[GPT-OCR] Regions provided for page {page_number}")
        found_page = False
        if "pages" in regions and isinstance(regions["pages"], list):
            for p in regions["pages"]:
                 p_num = p.get("page_number")
                 if str(p_num) == str(page_number):
                      found_page = True
                      r_list = p.get("regions", [])
                      for r in r_list:
                           if "bbox" in r:
                                bboxes.append(r["bbox"])
                      break
        if not found_page:
            print(f"[GPT-OCR] WARNING: Regions provided but page {page_number} not found.")

    # 2) Fallback to detection
    if not regions and not bboxes:
        print("[GPT-OCR] No regions provided (auto-mode). Running detection...")
        try:
            bboxes = detect_regions(image_path)
        except Exception as e:
            print(f"[GPT-OCR] Detection failed: {e}")
            bboxes = []

    # Fallback to full page if still empty
    if not bboxes:
         print("[GPT-OCR] No bboxes found/provided. Fallback to page-level.")
         bboxes = [[0, 0, width, height]]

    blocks: List[Dict[str, Any]] = []
    idx = 1
    
    # Prompt for transcription
    prompt = (
        "Transcribe the text in this image exactly as it appears. "
        "The image is a crop from a manga page. "
        "Output ONLY the text. If there is no text, or it is illegible, output nothing. "
        "Do not include any notes or explanations."
    )

    with tempfile.TemporaryDirectory() as temp_dir:
        for (x1, y1, x2, y2) in bboxes:
            # Validate coords
            x1, y1 = max(0, int(x1)), max(0, int(y1))
            x2, y2 = min(width, int(x2)), min(height, int(y2))
            
            if x2 <= x1 or y2 <= y1:
                continue

            crop = img.crop((x1, y1, x2, y2))
            
            # Save crop to temp file for the LLM client
            crop_filename = f"crop_{idx}.jpg"
            crop_path = os.path.join(temp_dir, crop_filename)
            crop.save(crop_path, format="JPEG", quality=95)
            
            print(f"[GPT-OCR] Processing block {idx}...")
            text = call_vision_llm(crop_path, prompt)
            text = (text or "").strip()
            
            # Remove markdown code blocks if present (common LLM artifact)
            if text.startswith("```"):
                lines = text.splitlines()
                if len(lines) >= 2:
                    text = "\n".join(lines[1:-1])
                text = text.replace("```", "").strip()

            print(f"[GPT-OCR] Block {idx}: '{text}'")

            if not text:
                # If explicit regions, keep empty blocks
                if not regions:
                    continue

            blocks.append(
                {
                    "block_id": f"t{idx}",
                    "original_text": text,
                    "bbox": [int(x1), int(y1), int(x2), int(y2)],
                    "is_speech": True,
                    "is_sfx": False,
                    "shape_hint": "unknown",
                    "max_characters": len(text),
                    "max_lines": text.count('\n') + 1,
                    "notes": "gpt4_vision",
                    "group_id": None,
                    "reading_order": None,
                    "block_type": "unknown",
                }
            )
            idx += 1

    # Fallback if result is empty
    if not blocks:
        blocks = [
            {
                "block_id": "t1",
                "original_text": "",
                "bbox": [0, 0, width, height],
                "is_speech": True,
                "is_sfx": False,
                "shape_hint": "unknown",
                "max_characters": 0,
                "max_lines": 0,
                "notes": "gpt4_empty_fallback",
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
