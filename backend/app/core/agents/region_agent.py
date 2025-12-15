from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from app.core.config import settings

# IMPORTANT:
# Use the detector that supports padding ("pad") so we can expand regions safely.
# app.ocr.detect_regions.detect_regions signature: (image_path, min_area, max_area_ratio, pad, ...)
from app.ocr.detect_regions import detect_regions


def region_agent(
    *,
    image_path: Path,
    page_number: int,
    image_filename: str,
    chapter_id: str = "001",
) -> dict:
    """Detect candidate text regions on a manga page.

    Returns a regions document compatible with the pipeline context:
    {
      "chapter_id": "...",
      "pages": [{
        "page_number": 1,
        "image_file": "001.jpg",
        "regions": [{"region_id":"r1","bbox":[x1,y1,x2,y2],...}],
        "notes": "detect_regions_v1"
      }]
    }
    """
    # Make it resilient if some settings are not defined yet.
    min_area = getattr(settings, "regions_min_area", 2500)
    max_area_ratio = getattr(settings, "regions_max_area_ratio", 0.40)
    pad = getattr(settings, "regions_pad", 8)
    max_regions = getattr(settings, "regions_max_regions", 0)  # 0 => unlimited

    boxes: List[List[int]] = detect_regions(
        str(image_path),
        min_area=int(min_area),
        max_area_ratio=float(max_area_ratio),
        pad=int(pad),
    )

    if max_regions and len(boxes) > int(max_regions):
        boxes = boxes[: int(max_regions)]

    regions = [
        {"region_id": f"r{i+1}", "bbox": box, "type_hint": "unknown", "score": 0}
        for i, box in enumerate(boxes)
    ]

    return {
        "chapter_id": chapter_id,
        "pages": [
            {
                "page_number": page_number,
                "image_file": image_filename,
                "regions": regions,
                "notes": "detect_regions_v1",
            }
        ],
    }
