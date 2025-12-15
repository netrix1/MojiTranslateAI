from fastapi import APIRouter, HTTPException
from app.schemas import JobCreated, JobSummary
from app.core.config import settings
from app.core.storage import ensure_dir, utc_now_iso, write_json, read_json
import uuid
from pathlib import Path

router = APIRouter()

def job_dir(job_id: str) -> Path:
    return settings.data_dir() / "jobs" / job_id

@router.post("/jobs", response_model=JobCreated)
def create_job():
    job_id = str(uuid.uuid4())
    jd = job_dir(job_id)
    ensure_dir(jd / "pages")
    ensure_dir(jd / "ocr" / "overrides")
    ensure_dir(jd / "checkpoints")
    ensure_dir(jd / "pipeline")
    meta = {"job_id": job_id, "status": "created", "created_on": utc_now_iso()}
    write_json(jd / "job.json", meta)
    return JobCreated(job_id=job_id, status="created")




def get_job_pages_status(job_id: str) -> list[dict]:
    jd = job_dir(job_id)
    pages_dir = jd / "pages"
    pipeline_dir = jd / "pipeline"
    pages_status = []
    
    if pages_dir.exists():
        images = sorted(list(pages_dir.glob("*.[jp][pn][g]")))
        for img in images:
            try:
                page_num = int(img.stem)
                state_file = pipeline_dir / f"state_page_{page_num:03d}.json"
                
                status = "pending"
                if state_file.exists():
                    # Check artifacts presence for status
                    has_final = (jd / "final" / f"{page_num:03d}.png").exists() or (jd / "final" / f"final_{page_num:03d}.png").exists()
                    has_cleaned = (jd / "cleaned" / f"{page_num:03d}.png").exists()
                    has_translation = (jd / "translation" / f"translation_page_{page_num:03d}.json").exists() # Actually translation is per job? No, per page results inside?
                    # Translation agent result is in pipeline state?
                    # Let's check state file "steps"
                    state = read_json(state_file)
                    
                    # More robust status check based on state
                    current_step = state.get("current_step", 0) # Index
                    # Simplified based on existence
                    
                    # Check if any step has error
                    steps_data = state.get("steps", {})
                    has_error = False
                    for k, v in steps_data.items():
                        if v.get("status") == "error":
                            has_error = True
                            break
                            
                    if has_error: status = "error"
                    elif has_final: status = "done"
                    elif has_cleaned: status = "typesetting"
                    elif has_translation: status = "cleaning" # heuristic
                    else: status = "active" # at least started
                
                pages_status.append({
                    "page_number": page_num,
                    "status": status
                })
            except:
                continue
    return pages_status

@router.get("/jobs/{job_id}")
def get_job(job_id: str):
    jd = job_dir(job_id)
    p = jd / "job.json"
    if not p.exists():
        raise HTTPException(status_code=404, detail="job_id not found")
        
    job_data = read_json(p)
    job_data["pages"] = get_job_pages_status(job_id)
    return job_data


@router.get("/jobs", response_model=list[JobSummary])
def list_jobs():
    jobs_dir = settings.data_dir() / "jobs"
    results = []
    if not jobs_dir.exists():
        return []
    
    for job_path in jobs_dir.iterdir():
        if job_path.is_dir():
            meta_path = job_path / "job.json"
            if meta_path.exists():
                try:
                    meta = read_json(meta_path)
                    pages_dir = job_path / "pages"
                    page_count = len(list(pages_dir.glob("*.jpg"))) if pages_dir.exists() else 0
                    
                    results.append(JobSummary(
                        job_id=meta.get("job_id", job_path.name),
                        status=meta.get("status", "unknown"),
                        created_on=meta.get("created_on"),
                        page_count=page_count,
                        pages=get_job_pages_status(meta.get("job_id", job_path.name))
                    ))
                except Exception:
                    continue
    
    # Sort by created_on desc
    results.sort(key=lambda x: x.created_on or "", reverse=True)
    return results

@router.delete("/jobs/{job_id}")
def delete_job(job_id: str):
    import shutil
    jd = job_dir(job_id)
    if not jd.exists():
        raise HTTPException(status_code=404, detail="Job not found")
    try:
        shutil.rmtree(jd)
        return {"status": "deleted", "job_id": job_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
