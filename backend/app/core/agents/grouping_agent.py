from __future__ import annotations

from typing import Any, Dict, List, Tuple


def _bbox(block: Dict[str, Any]) -> Tuple[int, int, int, int]:
    b = block.get("bbox") or [0, 0, 0, 0]
    if len(b) != 4:
        return (0, 0, 0, 0)
    return (int(b[0]), int(b[1]), int(b[2]), int(b[3]))


def _sort_blocks_reading_order_rtl(blocks: List[Dict[str, Any]], line_tol: int = 80) -> List[Dict[str, Any]]:
    """
    Ordenação v1 (mangá):
    - agrupa por 'linhas' (topo -> base) usando tolerância em y (y1)
    - dentro da linha: direita -> esquerda (x1 desc)
    """
    if not blocks:
        return []

    sorted_by_y = sorted(blocks, key=lambda b: _bbox(b)[1])

    lines: List[List[Dict[str, Any]]] = []
    for b in sorted_by_y:
        y1 = _bbox(b)[1]
        placed = False
        for line in lines:
            y_avg = sum(_bbox(x)[1] for x in line) / max(1, len(line))
            if abs(y1 - y_avg) <= line_tol:
                line.append(b)
                placed = True
                break
        if not placed:
            lines.append([b])

    for line in lines:
        line.sort(key=lambda b: _bbox(b)[0], reverse=True)

    ordered: List[Dict[str, Any]] = []
    for line in lines:
        ordered.extend(line)

    return ordered


def grouping_agent(ocr_raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    grouping_agent (v3):
    - schema-less
    - NÃO modifica o `ocr_raw` original (faz deep copy estrutural de pages/blocks)
    - ordena blocos em RTL e define group_id/reading_order
    """
    if not isinstance(ocr_raw, dict):
        raise TypeError("ocr_raw deve ser dict")

    doc: Dict[str, Any] = dict(ocr_raw)

    pages_in = ocr_raw.get("pages") or []
    if not isinstance(pages_in, list):
        pages_in = []

    pages_out: List[Dict[str, Any]] = []
    for page in pages_in:
        if not isinstance(page, dict):
            continue

        page_out = dict(page)

        blocks_in = page.get("blocks") or []
        if not isinstance(blocks_in, list):
            blocks_in = []

        blocks_copy = [dict(b) for b in blocks_in if isinstance(b, dict)]

        ordered = _sort_blocks_reading_order_rtl(blocks_copy, line_tol=80)

        for i, b in enumerate(ordered, start=1):
            b["group_id"] = f"g{i}"
            b["reading_order"] = i

        page_out["blocks"] = ordered
        pages_out.append(page_out)

    doc["pages"] = pages_out
    return doc
