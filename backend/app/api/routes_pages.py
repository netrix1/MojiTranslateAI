from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from app.schemas import UploadResult
from app.core.config import settings
from app.core.storage import ensure_dir
from pathlib import Path
import shutil

router = APIRouter()

def job_dir(job_id: str) -> Path:
    return settings.data_dir() / "jobs" / job_id

@router.post("/jobs/{job_id}/pages/{page_number}/image", response_model=UploadResult)
async def upload_page_image(job_id: str, page_number: int, file: UploadFile = File(...), background_tasks: BackgroundTasks = None):
    jd = job_dir(job_id)
    if not jd.exists():
        raise HTTPException(status_code=404, detail="job_id not found")

    pages_dir = ensure_dir(jd / "pages")
    ext = Path(file.filename).suffix.lower() or ".jpg"
    saved_name = f"{page_number:03d}{ext}"
    out_path = pages_dir / saved_name

    with out_path.open("wb") as f:
        shutil.copyfileobj(file.file, f)
        
    # Auto-start pipeline
    if background_tasks:
        from app.core.pipeline_engine import run_page_pipeline
        background_tasks.add_task(run_page_pipeline, job_id, page_number)

    # compat: retorno padroniza 001.jpg (quando for jpg); senão retorna o nome real
    return UploadResult(job_id=job_id, page_number=page_number, saved_as=f"{page_number:03d}.jpg" if ext==".jpg" else saved_name)


from fastapi.responses import FileResponse
from app.core.pipeline_engine import _page_image_path

@router.get("/jobs/{job_id}/pages/{page_number}/image")
def get_page_image(job_id: str, page_number: int):
    # Reusing logic from pipeline engine if possible, but importing private method is dirty.
    # Duplicating minimal logic or importing. I'll import from pipeline_engine as it's Python.
    p = _page_image_path(job_id, page_number)
    if not p.exists():
         raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(p)
