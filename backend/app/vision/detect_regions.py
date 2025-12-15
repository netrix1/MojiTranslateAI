from __future__ import annotations

from typing import Any, Dict, List, Tuple

import cv2


def _clip_bbox(x1: int, y1: int, x2: int, y2: int, w: int, h: int) -> Tuple[int, int, int, int]:
    x1 = max(0, min(int(x1), w - 1))
    y1 = max(0, min(int(y1), h - 1))
    x2 = max(0, min(int(x2), w))
    y2 = max(0, min(int(y2), h))
    if x2 <= x1:
        x2 = min(w, x1 + 1)
    if y2 <= y1:
        y2 = min(h, y1 + 1)
    return x1, y1, x2, y2


def detect_regions(
    image_path: str,
    *,
    min_area: int = 1500,
    max_area_ratio: float = 0.60,
    dilation: int = 3,
    blur: int = 3,
) -> List[Dict[str, Any]]:
    """
    Detecta regiões candidatas de texto/balões (baseline v1).

    Estratégia:
    - grayscale + blur
    - binarização adaptativa invertida (texto preto vira branco)
    - dilatação leve para unir caracteres em blocos
    - contornos + filtro por área

    Retorno:
      [{"region_id":"r1","bbox":[x1,y1,x2,y2],"type_hint":"unknown","score":0.0}, ...]
    """
    img = cv2.imread(image_path, cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(f"Não foi possível ler a imagem: {image_path}")

    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    if blur and blur > 1:
        k = blur if blur % 2 == 1 else blur + 1
        gray = cv2.GaussianBlur(gray, (k, k), 0)

    thr = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        35,
        11,
    )

    if dilation and dilation > 0:
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (dilation, dilation))
        thr = cv2.dilate(thr, kernel, iterations=1)

    contours, _ = cv2.findContours(thr, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    max_area = int(w * h * max_area_ratio)
    regions: List[Dict[str, Any]] = []
    rid = 0
    for c in contours:
        x, y, ww, hh = cv2.boundingRect(c)
        area = int(ww * hh)
        if area < min_area or area > max_area:
            continue
        x1, y1, x2, y2 = _clip_bbox(x, y, x + ww, y + hh, w, h)
        rid += 1
        regions.append(
            {
                "region_id": f"r{rid}",
                "bbox": [x1, y1, x2, y2],
                "type_hint": "unknown",
                "score": 0.0,
            }
        )

    # Ordenação inicial: topo->baixo, direita->esquerda (mangá)
    regions.sort(key=lambda r: (r["bbox"][1], -r["bbox"][0]))
    return regions
