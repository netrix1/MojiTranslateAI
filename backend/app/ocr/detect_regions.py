from __future__ import annotations

from dataclasses import dataclass
from typing import List

import cv2
import numpy as np


@dataclass(frozen=True)
class Region:
    x1: int
    y1: int
    x2: int
    y2: int

    def as_bbox(self) -> List[int]:
        return [int(self.x1), int(self.y1), int(self.x2), int(self.y2)]


def _clamp(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, v))


def _union(a: Region, b: Region) -> Region:
    return Region(
        x1=min(a.x1, b.x1),
        y1=min(a.y1, b.y1),
        x2=max(a.x2, b.x2),
        y2=max(a.y2, b.y2),
    )


def _overlap_ratio(a: Region, b: Region) -> float:
    # IoU simplificado
    ix1, iy1 = max(a.x1, b.x1), max(a.y1, b.y1)
    ix2, iy2 = min(a.x2, b.x2), min(a.y2, b.y2)
    iw, ih = max(0, ix2 - ix1), max(0, iy2 - iy1)
    inter = iw * ih
    if inter == 0:
        return 0.0
    area_a = (a.x2 - a.x1) * (a.y2 - a.y1)
    area_b = (b.x2 - b.x1) * (b.y2 - b.y1)
    return inter / float(area_a + area_b - inter + 1e-9)


def _are_close_or_overlapping(a: Region, b: Region, dist_threshold: int = 20) -> bool:
    """
    Returns True if regions overlap OR are within dist_threshold pixels of each other.
    """
    # Simply check if expanding one by threshold makes them overlap
    # Or check gap
    x_overlap = max(0, min(a.x2, b.x2) - max(a.x1, b.x1)) > 0
    y_overlap = max(0, min(a.y2, b.y2) - max(a.y1, b.y1)) > 0
    
    if x_overlap and y_overlap:
        return True
        
    # Check proximity
    # If they overlap in X, check Y distance. If overlap in Y, check X distance.
    # This assumes we want to merge things that are aligned.
    
    # Generic distance check:
    x_gap = max(0, a.x1 - b.x2, b.x1 - a.x2)
    y_gap = max(0, a.y1 - b.y2, b.y1 - a.y2)
    
    return x_gap <= dist_threshold and y_gap <= dist_threshold

def _merge_overlapping(regions: List[Region], iou_threshold: float = 0.10, dist_threshold: int = 25) -> List[Region]:
    # Aggressive merge: IO > threshold OR Distance < threshold
    if not regions:
        return regions

    # Sort large to small helps allow big bubbles to eat small ones inside/near them
    regions = sorted(regions, key=lambda r: ((r.x2 - r.x1) * (r.y2 - r.y1)), reverse=True)
    merged: List[Region] = []

    while regions:
        current = regions.pop(0)
        changed = True
        while changed:
            changed = False
            keep: List[Region] = []
            for r in regions:
                # Merge if close/overlapping OR if one is inside another (implied by union of close)
                if _are_close_or_overlapping(current, r, dist_threshold=dist_threshold):
                    current = _union(current, r)
                    changed = True
                else:
                    keep.append(r)
            regions = keep
        merged.append(current)

    return merged


def _sort_reading_order_rtl(regions: List[Region], line_tol: int = 60) -> List[Region]:
    """
    Ordena por leitura típica de mangá:
    - agrupa por 'linhas' (y) e ordena da direita para esquerda dentro da linha
    - linhas de cima para baixo
    """
    if not regions:
        return regions

    regs = sorted(regions, key=lambda r: r.y1)
    lines: List[List[Region]] = []
    for r in regs:
        placed = False
        for line in lines:
            y_avg = sum(x.y1 for x in line) / len(line)
            if abs(r.y1 - y_avg) <= line_tol:
                line.append(r)
                placed = True
                break
        if not placed:
            lines.append([r])

    for line in lines:
        line.sort(key=lambda r: r.x1, reverse=True)

    ordered: List[Region] = []
    for line in lines:
        ordered.extend(line)

    return ordered


def detect_regions(
    image_path: str,
    *,
    min_area: int = 2000,
    max_area_ratio: float = 0.40,
    pad: int = 8,
) -> List[List[int]]:
    """
    Detector v1 (heurístico):
    - binariza para destacar texto/traços
    - usa morfologia para unir caracteres em “blocos”
    - extrai contornos e filtra por área
    - mescla caixas que se sobrepõem
    - ordena em leitura RTL

    Retorna lista de bbox no formato [x1,y1,x2,y2].
    """
    img = cv2.imread(image_path, cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(f"Não foi possível abrir a imagem: {image_path}")

    h, w = img.shape[:2]
    max_area = int((w * h) * max_area_ratio)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Binarização robusta (texto/traços -> branco em fundo preto)
    # Increased block size for better local handling
    thr = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_MEAN_C,
        cv2.THRESH_BINARY_INV,
        45, 10
    )

    # Morfologia: unir caracteres em regiões
    # Dynamic kernel size based on image width (approx 1% of width)
    # Ensures odd number
    k_size = max(5, int(w / 120))
    if k_size % 2 == 0:
        k_size += 1
        
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (k_size, k_size))
    mor = cv2.morphologyEx(thr, cv2.MORPH_CLOSE, kernel, iterations=2) # Increased iterations to fuse better
    # mor = cv2.dilate(mor, kernel, iterations=1) # Dilate usually overkill if close is aggressive

    contours, _ = cv2.findContours(mor, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    regions: List[Region] = []
    for c in contours:
        x, y, cw, ch = cv2.boundingRect(c)
        area = cw * ch
        if area < min_area:
            continue
        if area > max_area:
            continue

        # Aspect Ratio filtering
        ratio = cw / float(ch)
        if ratio > 6.0 or ratio < 0.15: # Ignore very thin or very tall lines
            continue

        x1 = _clamp(x - pad, 0, w)
        y1 = _clamp(y - pad, 0, h)
        x2 = _clamp(x + cw + pad, 0, w)
        y2 = _clamp(y + ch + pad, 0, h)

        # descarta caixas degeneradas
        if (x2 - x1) < 20 or (y2 - y1) < 20:
            continue

        regions.append(Region(x1, y1, x2, y2))

    regions = _merge_overlapping(regions, iou_threshold=0.10) # Lower threshold to merge more aggressively
    regions = _sort_reading_order_rtl(regions, line_tol=70)

    return [r.as_bbox() for r in regions]
