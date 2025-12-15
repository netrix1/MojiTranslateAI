from __future__ import annotations

import cv2
from typing import Dict


def draw_regions_preview(image_path: str, regions_doc: Dict, output_path: str) -> None:
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(image_path)

    for page in regions_doc.get("pages", []):
        for r in page.get("regions", []):
            x1, y1, x2, y2 = r["bbox"]
            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
            rid = r.get("region_id", "")
            cv2.putText(img, rid, (x1 + 4, y1 + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

    cv2.imwrite(output_path, img)
