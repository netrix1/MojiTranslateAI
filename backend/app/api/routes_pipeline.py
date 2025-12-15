from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Body, BackgroundTasks

from app.core.config import settings
from app.core.pipeline_engine import run_page_pipeline, approve_checkpoint, load_pipeline_def
from app.core.storage import read_json, ensure_dir

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


def job_dir(job_id: str) -> Path:
    return settings.data_dir() / "jobs" / job_id


@router.post("/reset/{job_id}/{page_number}")
def reset_pipeline_state(job_id: str, page_number: int, step: int = 0):
    from app.core.pipeline_engine import load_state, save_state
    state = load_state(job_id, page_number)
    state["current_step"] = step
    # Reset checkpoints status if going back? 
    # For now, simplistic reset of pointer is enough to force re-execution of agents.
    save_state(job_id, page_number, state)
    return state


@router.post("/{job_id}/step/{step_id}/rerun/{page_number}")
def rerun_step(job_id: str, step_id: str, page_number: int):
    """
    Resets the pipeline state to point to the request step_id, effectively allowing a re-run.
    """
    from app.core.pipeline_engine import load_state, save_state
    
    # 1. Load Definition to find index
    pipeline_def = load_pipeline_def()
    steps = pipeline_def.get("steps", [])
    
    target_index = -1
    for i, s in enumerate(steps):
        if s.get("id") == step_id:
            target_index = i
            break
            
    if target_index == -1:
        raise HTTPException(status_code=404, detail=f"Step {step_id} not found in pipeline definition")
        
    # 2. Update State
    state = load_state(job_id, page_number)
    state["current_step"] = target_index
    
    # Optional: Clear the status of this step so it doesn't look 'done' immediately if we just view state
    if step_id in state.get("steps", {}):
        state["steps"][step_id]["status"] = "pending"
        
    save_state(job_id, page_number, state)
    
    # 3. Trigger Run
    return run_page_pipeline(job_id=job_id, page_number=page_number)


@router.post("/run/{job_id}/page/{page_number}")
def run_pipeline(job_id: str, page_number: int):
    return run_page_pipeline(job_id=job_id, page_number=page_number)


@router.post("/{job_id}/checkpoints/{checkpoint_id}/approve")
def approve(job_id: str, checkpoint_id: str):
    try:
        return approve_checkpoint(job_id=job_id, checkpoint_id=checkpoint_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="checkpoint_id not found")


@router.get("/{job_id}/ocr/raw")
def get_ocr_raw(job_id: str):
    p = job_dir(job_id) / "ocr" / "ocr_raw.json"
    if not p.exists():
        raise HTTPException(status_code=404, detail="ocr_raw not found")
    return read_json(p)


@router.get("/{job_id}/ocr/grouped")
def get_ocr_grouped(job_id: str):
    p = job_dir(job_id) / "ocr" / "ocr_grouped.json"
    if not p.exists():
        raise HTTPException(status_code=404, detail="ocr_grouped not found")
    return read_json(p)


@router.get("/{job_id}/ocr/final")
def get_ocr_final(job_id: str):
    p = job_dir(job_id) / "ocr" / "ocr_final.json"
    if not p.exists():
        raise HTTPException(status_code=404, detail="ocr_final not found")
    return read_json(p)


@router.get("/{job_id}/translation")
def get_translation(job_id: str):
    p = job_dir(job_id) / "translation" / "translation.json"
    if not p.exists():
        raise HTTPException(status_code=404, detail="translation not found")
    return read_json(p)


@router.put("/{job_id}/translation")
def update_translation(job_id: str, translation: dict = Body(...)):
    p = job_dir(job_id) / "translation" / "translation.json"
    ensure_dir(p.parent)
    from app.core.storage import write_json
    write_json(p, translation)
    return {"status": "updated", "file": p.name}


@router.get("/{job_id}/regions/{page_number}")
def get_regions(job_id: str, page_number: int):
    p = job_dir(job_id) / "regions" / f"regions_page_{page_number:03d}.json"
    if not p.exists():
        raise HTTPException(status_code=404, detail="regions not found")
    return read_json(p)


@router.put("/{job_id}/regions/{page_number}")
def update_regions(job_id: str, page_number: int, regions: dict = Body(...), background_tasks: BackgroundTasks = None):
    p = job_dir(job_id) / "regions" / f"regions_page_{page_number:03d}.json"
    ensure_dir(p.parent)
    
    from app.core.storage import write_json, read_json
    from app.core.pipeline_engine import load_state, save_state, run_page_pipeline
    
    write_json(p, regions)
    
    # Logic: If regions changed, we should invalidate OCR downstream and re-run?
    # User request: "When I enter OCR screen, run on defined coordinates".
    # This implies auto-run.
    
    # 1. Reset OCR step to pending (index 2 usually, or find by id 'ocr')
    state = load_state(job_id, page_number)
    steps = state.get("steps", {})
    
    # Find override: simply set 'ocr' step to pending if it was done
    if "ocr" in steps: # Assuming step id is 'ocr'
         steps["ocr"]["status"] = "pending"
         state["steps"] = steps
         # Reset current_step to OCR index?
         # Pipeline def has 'regions' (0), 'regions_human'(1), 'ocr'(2).
         # If we are at regions_human and approve/save, we should be ready form OCR.
         # If we set current_step to 2 (OCR), run_page_pipeline will execute it.
         
         # Let's find index of 'ocr'
         # We can't load pipeline def easily here without import, but let's assume standard flow
         # Or just let the engine handle it.
         save_state(job_id, page_number, state)

    # 2. Trigger Pipeline Run in Background
    if background_tasks:
        # We assume after saving regions, we want to proceed/update OCR
        # But wait, we are usually PAUSED at regions_human (checkpoint).
        # We need to Approve checkpoint? Or just Run?
        # If paused at checkpoint, 'run_page_pipeline' checks checkpoint status.
        # It needs 'approved'.
        # Does "Save Regions" imply "Approve"?
        # Usually separate button. But if user says "When I enter OCR screen", they clicked "Next" which implies moving on.
        # But 'Next' in frontend is silent.
        # Maybe we should AUTO-APPROVE checkpoint here if it matches?
        
        # Simpler: just trigger run. If checkpoint allows, it runs. If not, it waits.
        # But for OCR to run, we must pass the checkpoint. 
        # If user is stuck at checkpoint, OCR won't run.
        # User dilemma: "Enter OCR screen -> runs on coordinates".
        # This implies they bypassed checkpoint or checkpoint is done.
        
        # Let's just trigger the run. If the user hasn't approved, it won't run OCR.
        # BUT if they are AT the OCR screen, they assume it runs.
        # We will assume saving regions updates data.
        # We will add a task to rerun from OCR step? That skips checkpoint.
        # Rerunning from 'ocr' step seems invalid if we enforce checkpoints.
        # But `rerun_step` exists exactly for this: "Refresh".
        
        # Hack/Feature: Auto-Rerun OCR step
        background_tasks.add_task(rerun_ocr_step_auto, job_id, page_number)

    return {"status": "updated", "file": p.name}

def rerun_ocr_step_auto(job_id: str, page_number: int):
    # This function mimics rerun_step('ocr') logic
    from app.core.pipeline_engine import load_state, save_state, load_pipeline_def, run_page_pipeline
    
    # Find OCR step index
    pipeline_def = load_pipeline_def()
    steps = pipeline_def.get("steps", [])
    target_index = -1
    for i, s in enumerate(steps):
        if s.get("id") == "ocr":
            target_index = i
            break
            
    if target_index >= 0:
        state = load_state(job_id, page_number)
        state["current_step"] = target_index
        # Validate we aren't jumping excessively? 
        # Usually regions is step 0. OCR is step 2. Jumping over human checkpoint (1)?
        # If user saves regions, they implicitly are done with regions.
        save_state(job_id, page_number, state)
        run_page_pipeline(job_id, page_number)


@router.put("/{job_id}/ocr/{page_number}")
def update_ocr(job_id: str, page_number: int, blocks: list[dict] = Body(...), background_tasks: BackgroundTasks = None):
    p = job_dir(job_id) / "ocr" / "ocr_final.json"
    ensure_dir(p.parent)

    if p.exists():
        data = read_json(p)
    else:
        p_grouped = job_dir(job_id) / "ocr" / "ocr_grouped.json"
        if p_grouped.exists():
             data = read_json(p_grouped)
        else:
             data = {"job_id": job_id, "pages": []}
    pages = data.get("pages", [])
    
    # Locate the page
    target_page = None
    for page in pages:
        if page.get("page_number") == page_number:
            target_page = page
            break
            
    if not target_page:
        target_page = {"page_number": page_number, "blocks": []}
        pages.append(target_page)
        
    target_page["blocks"] = blocks
    data["pages"] = pages
    
    from app.core.storage import write_json
    write_json(p, data)
    
    # --- Auto-Advance Logic ---
    from app.core.pipeline_engine import load_state, save_state, run_page_pipeline
    
    # 1. Approve ocr_human checkpoint
    state = load_state(job_id, page_number)
    steps = state.get("steps", {})
    if "ocr_human" in steps:
        steps["ocr_human"]["status"] = "approved"
        state["steps"] = steps
        save_state(job_id, page_number, state)
        
    # 2. Trigger Pipeline Run (Translation Agent)
    if background_tasks:
        background_tasks.add_task(run_page_pipeline, job_id, page_number)
    # --------------------------
    
    return {"status": "updated", "page_number": page_number}

@router.get("/{job_id}/cleaned/{page_number}/image")
def get_cleaned_image(job_id: str, page_number: int):
    from fastapi import Response
    # Try different extensions
    base = job_dir(job_id) / "cleaned"
    
    # The engine saves as stems from original, but force saved as .png usually
    target = base / f"{page_number:03d}.png"
    media_type = "image/png"
    if not target.exists():
         target = base / f"{page_number:03d}.jpg"
         media_type = "image/jpeg"
    
    if not target.exists():
        raise HTTPException(status_code=404, detail="Cleaned image not found")
        
    # Read into memory to avoid Content-Length race conditions on WSL
    return Response(content=target.read_bytes(), media_type=media_type)


@router.get("/{job_id}/redraw/{page_number}/image")
def get_redraw_image(job_id: str, page_number: int):
    from fastapi import Response
    base = job_dir(job_id) / "redraw"
    target = base / f"{page_number:03d}.png"
    media_type = "image/png"
    if not target.exists():
         target = base / f"{page_number:03d}.jpg"
         media_type = "image/jpeg"
    
    if not target.exists():
        raise HTTPException(status_code=404, detail="Redraw image not found")
        
    return Response(content=target.read_bytes(), media_type=media_type)


@router.get("/{job_id}/final/{page_number}/image")
def get_final_image(job_id: str, page_number: int):
    from fastapi import Response
    base = job_dir(job_id) / "final"
    target = base / f"{page_number:03d}.png"
    media_type = "image/png"
    if not target.exists():
         target = base / f"{page_number:03d}.jpg"
         media_type = "image/jpeg"
    
    if not target.exists():
        raise HTTPException(status_code=404, detail="Final image not found")
        
    return Response(content=target.read_bytes(), media_type=media_type)


@router.get("/{job_id}/state/{page_number}")
def get_pipeline_state(job_id: str, page_number: int):
    from app.core.pipeline_engine import load_state
    return load_state(job_id, page_number)
