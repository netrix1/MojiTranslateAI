from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path

from app.core.pipeline_engine import _job_dir
from app.vision.draw_regions_preview import draw_regions_preview

router = APIRouter()


@router.get("/pipeline/{job_id}/regions/{page_number}/preview")
def get_regions_preview(job_id: str, page_number: int):
    """
    Gera (se necessário) e retorna a imagem de preview das regiões
    para o job/página informados.
    """
    job_dir = _job_dir(job_id)
    if not job_dir.exists():
        raise HTTPException(status_code=404, detail="job not found")

    # 1) Localizar imagem da página
    pages_dir = job_dir / "pages"
    img_path: Path | None = None
    for ext in (".jpg", ".jpeg", ".png", ".webp"):
        candidate = pages_dir / f"{page_number:03d}{ext}"
        if candidate.exists():
            img_path = candidate
            break

    if img_path is None:
        raise HTTPException(status_code=404, detail="page image not found")

    # 2) JSON de regiões
    regions_json = job_dir / "regions" / f"regions_page_{page_number:03d}.json"
    if not regions_json.exists():
        raise HTTPException(status_code=404, detail="regions json not found")

    # 3) Caminho do preview em disco (cache)
    preview_path = job_dir / "regions" / f"regions_page_{page_number:03d}.preview.jpg"

    try:
        # Sempre gera novamente (é barato e garante que está atualizado);
        # se preferir cache agressivo, basta checar preview_path.exists()
        draw_regions_preview(
            image_path=str(img_path),
            regions_path=str(regions_json),
            output_path=str(preview_path),
        )
    except Exception as exc:  # pragma: no cover
        raise HTTPException(
            status_code=500,
            detail=f"error generating preview: {exc}",
        )

    if not preview_path.exists():
        raise HTTPException(status_code=500, detail="preview generation failed")

    return FileResponse(str(preview_path), media_type="image/jpeg")
