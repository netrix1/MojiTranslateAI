from __future__ import annotations

from pathlib import Path
import uuid
from typing import Any, Dict

from app.core.config import settings
from app.core.storage import ensure_dir, write_json, read_json, utc_now_iso
from app.core.tools.ocr_router import run_ocr
from app.core.agents.region_agent import region_agent
from app.core.agents.grouping_agent import grouping_agent
from app.core.agents.ocr_editor_agent import ocr_editor_agent


def _job_dir(job_id: str) -> Path:
    return settings.data_dir() / "jobs" / job_id


def _page_image_path(job_id: str, page_number: int) -> Path:
    pages_dir = _job_dir(job_id) / "pages"
    for ext in [".jpg", ".jpeg", ".png", ".webp"]:
        p = pages_dir / f"{page_number:03d}{ext}"
        if p.exists():
            return p
    return pages_dir / f"{page_number:03d}.jpg"


def _ocr_paths(job_id: str) -> Dict[str, Path]:
    base = _job_dir(job_id) / "ocr"
    return {
        "raw": base / "ocr_raw.json",
        "grouped": base / "ocr_grouped.json",
        "final": base / "ocr_final.json",
        "overrides_dir": base / "overrides",
    }


def _regions_path(job_id: str, page_number: int) -> Path:
    base = _job_dir(job_id) / "regions"
    return base / f"regions_page_{page_number:03d}.json"


def _state_path(job_id: str, page_number: int) -> Path:
    return _job_dir(job_id) / "pipeline" / f"state_page_{page_number:03d}.json"


def _checkpoint_dir(job_id: str) -> Path:
    return _job_dir(job_id) / "checkpoints"


def load_pipeline_def() -> dict:
    p = Path(settings.pipeline_path)
    return read_json(p)


def load_state(job_id: str, page_number: int) -> dict:
    sp = _state_path(job_id, page_number)
    if sp.exists():
        return read_json(sp)
    return {"job_id": job_id, "page_number": page_number, "current_step": 0, "steps": {}, "checkpoint_id": None, "checkpoint_ids": {}}


def save_state(job_id: str, page_number: int, state: dict) -> None:
    write_json(_state_path(job_id, page_number), state)


def create_checkpoint(job_id: str, page_number: int, label: str, context: dict) -> str:
    cid = str(uuid.uuid4())
    cp = {
        "checkpoint_id": cid,
        "job_id": job_id,
        "page_number": page_number,
        "label": label,
        "status": "awaiting_human",
        "created_on": utc_now_iso(),
        "approved_on": None,
        "context_keys": list(context.keys()),
        "context": context,
    }
    ensure_dir(_checkpoint_dir(job_id))
    write_json(_checkpoint_dir(job_id) / f"{cid}.json", cp)
    return cid


def approve_checkpoint(job_id: str, checkpoint_id: str) -> dict:
    p = _checkpoint_dir(job_id) / f"{checkpoint_id}.json"
    if not p.exists():
        raise FileNotFoundError("checkpoint_id not found")
    cp = read_json(p)
    cp["status"] = "approved"
    cp["approved_on"] = utc_now_iso()
    write_json(p, cp)
    return cp


def get_checkpoint(job_id: str, checkpoint_id: str) -> dict:
    p = _checkpoint_dir(job_id) / f"{checkpoint_id}.json"
    if not p.exists():
        raise FileNotFoundError("checkpoint_id not found")
    return read_json(p)


from app.core.logging import logger
import traceback

# ... imports ...

def run_page_pipeline(job_id: str, page_number: int) -> dict:
    pipe = load_pipeline_def()
    steps = pipe.get("steps", [])
    state = load_state(job_id, page_number)

    # Defaults defensivos (evita state "quebrado" de versões anteriores)
    state.setdefault("steps", {})
    state.setdefault("checkpoint_ids", {})

    logger.info(f"--- RUN job={job_id} page={page_number} ---")
    logger.info(f"Pipeline definition: {len(steps)} steps loaded.")
    
    img_path = _page_image_path(job_id, page_number)
    
    ctx: Dict[str, Any] = {
        "job_id": job_id,
        "page_number": page_number,
        "image_filename": img_path.name,
    }

    # Load artifacts if they already exist
    ocrp = _ocr_paths(job_id)
    if ocrp["raw"].exists():
        ctx["ocr_raw"] = read_json(ocrp["raw"])
    if ocrp["grouped"].exists():
        ctx["ocr_grouped"] = read_json(ocrp["grouped"])
    if ocrp["final"].exists():
        ctx["ocr_final"] = read_json(ocrp["final"])

    rp = _regions_path(job_id, page_number)
    if rp.exists():
        ctx["regions"] = read_json(rp)

    tp = _job_dir(job_id) / "translation" / "translation.json"
    if tp.exists():
        ctx["translation"] = read_json(tp)

    # Hydrate image paths if they exist
    # Standard naming: {page_number:03d}.png in respective folders
    clean_img = _job_dir(job_id) / "cleaned" / f"{page_number:03d}.png"
    if clean_img.exists():
        ctx["cleaned_image"] = clean_img.name

    redraw_img = _job_dir(job_id) / "redraw" / f"{page_number:03d}.png"
    if not redraw_img.exists(): # Try jpg
         redraw_img = _job_dir(job_id) / "redraw" / f"{page_number:03d}.jpg"
    
    if redraw_img.exists():
        ctx["redraw_image"] = redraw_img.name

    i = int(state.get("current_step", 0))

    while i < len(steps):
        step = steps[i]
        step_id = step.get("id", f"step{i}")
        stype = step.get("type")

        state["current_step"] = i
        logger.info(f"Executing step {i}: {step.get('id')} ({stype})")
        save_state(job_id, page_number, state)

        try:
            # 1) Regions stage
            if stype == "agent" and step.get("name") == "region_agent":
                regions_doc = region_agent(
                    image_path=img_path,
                    page_number=page_number,
                    image_filename=img_path.name,
                )
                ensure_dir(_job_dir(job_id) / "regions")
                write_json(_regions_path(job_id, page_number), regions_doc)

                ctx["regions"] = regions_doc
                state["steps"][step_id] = {"status": "done", "completed_on": utc_now_iso()}
                save_state(job_id, page_number, state)

                i += 1
                state["current_step"] = i
                save_state(job_id, page_number, state)
                continue

            # 2) OCR stage
            if stype == "tool" and step.get("name", "").startswith("ocr"):
                # Force reload regions to ensure fresh data (e.g. if updated via API while pipeline running)
                rp_path = _regions_path(job_id, page_number)
                if rp_path.exists():
                     ctx["regions"] = read_json(rp_path)
                     logger.info(f"Force-reloaded regions from {rp_path.name}")
                else:
                     logger.warning(f"Regions file missing at {rp_path}")
                
                logger.info(f"Running OCR. keys={list(ctx.keys())}")
                if "regions" in ctx:
                     r = ctx["regions"]
                     logger.info(f"Regions context present. Pages: {len(r.get('pages', []))}")
                else:
                     logger.warning("Regions context MISSING in run_page_pipeline")
                     
                doc = run_ocr(
                    page_number=page_number, 
                    image_path=img_path, 
                    regions=ctx.get("regions")
                )
                write_json(ocrp["raw"], doc)
                ctx["ocr_raw"] = doc

                state["steps"][step_id] = {"status": "done", "completed_on": utc_now_iso()}
                save_state(job_id, page_number, state)

                i += 1
                state["current_step"] = i
                save_state(job_id, page_number, state)
                continue

            # 3) Grouping stage
            if stype == "agent" and step.get("name") == "grouping_agent":
                grouped = grouping_agent(ctx["ocr_raw"])
                write_json(ocrp["grouped"], grouped)
                ctx["ocr_grouped"] = grouped

                state["steps"][step_id] = {"status": "done", "completed_on": utc_now_iso()}
                save_state(job_id, page_number, state)

                i += 1
                state["current_step"] = i
                save_state(job_id, page_number, state)
                continue

            # 4) Human checkpoint stage (1 checkpoint por step_id)
            if stype == "human_checkpoint":
                label = step.get("label", "Validação humana")

                cid_map = state.get("checkpoint_ids", {})
                cid = cid_map.get(step_id)

                # Compat com state antigo (se existir)
                if not cid and state.get("checkpoint_id"):
                    cid = state["checkpoint_id"]
                    cid_map[step_id] = cid
                    state["checkpoint_ids"] = cid_map
                    state["checkpoint_id"] = None
                    save_state(job_id, page_number, state)

                if not cid:
                    cid = create_checkpoint(
                        job_id,
                        page_number,
                        label,
                        {
                            "job_id": job_id,
                            "page_number": page_number,
                            "image_filename": ctx["image_filename"],
                            "regions": ctx.get("regions"),
                            "ocr_raw": ctx.get("ocr_raw"),
                            "ocr_grouped": ctx.get("ocr_grouped"),
                        },
                    )
                    cid_map[step_id] = cid
                    state["checkpoint_ids"] = cid_map
                    save_state(job_id, page_number, state)

                    return {
                        "status": "awaiting_human",
                        "checkpoint_id": cid,
                        "checkpoint_step_id": step_id,
                        "checkpoint_label": label,
                        "context": {k: ctx.get(k) for k in ["job_id", "page_number", "image_filename", "regions", "ocr_raw", "ocr_grouped"]},
                    }

                cp = get_checkpoint(job_id, cid)

                # Se não aprovado, para aqui (correto)
                if cp.get("status") != "approved":
                    save_state(job_id, page_number, state)
                    return {
                        "status": "awaiting_human",
                        "checkpoint_id": cid,
                        "checkpoint_step_id": step_id,
                        "checkpoint_label": label,
                        "context": {k: ctx.get(k) for k in ["job_id", "page_number", "image_filename", "regions", "ocr_raw", "ocr_grouped"]},
                    }

                # ✅ Se aprovado, marca step como done e segue
                state["steps"][step_id] = {
                    "status": "done",
                    "completed_on": utc_now_iso(),
                    "checkpoint_id": cid,
                }

                i += 1
                state["current_step"] = i
                save_state(job_id, page_number, state)
                continue

            # 5) OCR editor / merge stage
            if stype == "agent" and step.get("name") == "ocr_editor_agent":
                final_doc, overrides = ocr_editor_agent(ctx["ocr_grouped"])

                ensure_dir(ocrp["overrides_dir"])
                ofn = ocrp["overrides_dir"] / f"auto_{utc_now_iso().replace(':', '').replace('-', '')}.json"
                write_json(ofn, {"ops": overrides, "generated_on": utc_now_iso(), "engine": "ocr_editor_agent"})

                write_json(ocrp["final"], final_doc)
                ctx["ocr_final"] = final_doc

                state["steps"][step_id] = {"status": "done", "completed_on": utc_now_iso(), "overrides_file": ofn.name}

                i += 1
                state["current_step"] = i
                save_state(job_id, page_number, state)
                continue # Fixed double increment logic in original

            # 6) Translation stage
            if stype == "agent" and step.get("name") == "translation_agent":
                # Ensure ocr_final exists in ctx or load it
                if "ocr_final" not in ctx:
                     # Should have been loaded or created
                     pass 

                from app.core.agents.translation_agent import translation_agent
                trans_doc = translation_agent(ctx["ocr_final"])
                
                # Save translation
                trans_path = _job_dir(job_id) / "translation"
                ensure_dir(trans_path)
                outfile = trans_path / "translation.json"
                write_json(outfile, trans_doc)
                
                ctx["translation"] = trans_doc
                state["steps"][step_id] = {"status": "done", "completed_on": utc_now_iso()}
                
                i += 1
                state["current_step"] = i
                save_state(job_id, page_number, state)
                continue

            # 7) Cleaning stage
            if stype == "agent" and step.get("name") == "cleaning_agent":
                # Ensure regions exist
                if "regions" not in ctx:
                     # Load regions
                     pass
                
                from app.core.agents.cleaning_agent import cleaning_agent
                cleaned_img = cleaning_agent(img_path, ctx["regions"])
                
                # Save cleaned image
                clean_dir = _job_dir(job_id) / "cleaned"
                ensure_dir(clean_dir)
                out_img_path = clean_dir / f"{img_path.stem}.png" # Save as png
                cleaned_img.save(out_img_path)
                
                ctx["cleaned_image"] = out_img_path.name
                state["steps"][step_id] = {"status": "done", "completed_on": utc_now_iso(), "file": out_img_path.name}
                
                i += 1
                state["current_step"] = i
                save_state(job_id, page_number, state)
                continue

            # 8) Redraw stage (Inpainting)
            if stype == "agent" and step.get("name") == "redraw_agent":
                # Uses original image + regions to generate inpainted version
                if "regions" not in ctx:
                     pass
                
                from app.core.agents.redraw_agent import redraw_agent
                redraw_img = redraw_agent(img_path, ctx["regions"])
                
                # Save redraw image
                redraw_dir = _job_dir(job_id) / "redraw"
                ensure_dir(redraw_dir)
                out_redraw_path = redraw_dir / f"{img_path.stem}.png"
                redraw_img.save(out_redraw_path)
                
                ctx["redraw_image"] = out_redraw_path.name
                state["steps"][step_id] = {"status": "done", "completed_on": utc_now_iso(), "file": out_redraw_path.name}
                
                i += 1
                state["current_step"] = i
                save_state(job_id, page_number, state)
                continue

            # 9) Typesetting stage
            if stype == "agent" and step.get("name") == "typesetting_agent":
                # Require: redraw_image OR cleaned_image, translation, regions
                # Load if missing
                if "translation" not in ctx:
                     # Should load
                     pass 
                if "regions" not in ctx:
                     pass
                
                # PREFER Redraw Image, Fallback to Cleaned, Fallback to Original
                base_img_path = img_path
                
                if "redraw_image" in ctx:
                     redraw_dir = _job_dir(job_id) / "redraw"
                     p = redraw_dir / ctx["redraw_image"]
                     if p.exists():
                          base_img_path = p
                elif "cleaned_image" in ctx:
                     clean_dir = _job_dir(job_id) / "cleaned"
                     p = clean_dir / ctx["cleaned_image"]
                     if p.exists():
                          base_img_path = p
                
                from app.core.agents.typesetting_agent import typesetting_agent
                
                # Filtering translation for this page
                # ctx["translation"] is the full doc
                page_trans = {"blocks": []}
                if "pages" in ctx.get("translation", {}):
                     for p in ctx["translation"]["pages"]:
                          if p.get("page_number") == page_number:
                               page_trans = p
                               break
                
                final_img = typesetting_agent(base_img_path, page_trans, ctx["regions"], original_image_path=str(img_path))
                
                # Save final
                final_dir = _job_dir(job_id) / "final"
                ensure_dir(final_dir)
                out_final = final_dir / f"{img_path.stem}.png"
                final_img.save(out_final)
                
                ctx["final_image"] = out_final.name
                state["steps"][step_id] = {"status": "done", "completed_on": utc_now_iso(), "file": out_final.name}
                
                i += 1
                state["current_step"] = i
                save_state(job_id, page_number, state)
                continue

            # fallback
            logger.warning(f"Unknown step: {step_id} - skipping")
            state["steps"][step_id] = {"status": "skipped", "completed_on": utc_now_iso(), "reason": "unknown step"}
            i += 1
            state["current_step"] = i
            save_state(job_id, page_number, state)

        except Exception as e:
            logger.error(f"Error in step {step_id}: {e}")
            logger.error(traceback.format_exc())
            state["steps"][step_id] = {
                "status": "error", 
                "error": str(e), 
                "failed_on": utc_now_iso()
            }
            save_state(job_id, page_number, state)
            return {
                "status": "failed",
                "step_id": step_id,
                "error": str(e)
            }

    state["current_step"] = len(steps)
    save_state(job_id, page_number, state)

    return {
        "status": "completed",
        "checkpoint_id": None,
        "context": {k: ctx.get(k) for k in ["job_id", "page_number", "image_filename", "regions", "ocr_raw", "ocr_grouped", "ocr_final"]},
    }
