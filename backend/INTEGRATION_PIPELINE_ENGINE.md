# Integração no pipeline_engine.py (sugestão)

1) Import:
from app.core.agents.region_agent import region_agent

2) Helper:
def _regions_path(job_id: str, page_number: int) -> Path:
    base = _job_dir(job_id) / "regions"
    return base / f"regions_page_{page_number:03d}.json"

3) Load no ctx (antes do loop):
rp = _regions_path(job_id, page_number)
if rp.exists():
    ctx["regions"] = read_json(rp)

4) Step handler:
if stype == "agent" and step.get("name") == "region_agent":
    img_path = _page_image_path(job_id, page_number)
    regions_doc = region_agent(image_path=img_path, page_number=page_number, image_filename=img_path.name)
    ensure_dir(_job_dir(job_id) / "regions")
    write_json(_regions_path(job_id, page_number), regions_doc)
    ctx["regions"] = regions_doc
    state["steps"][step_id] = {"status": "done", "completed_on": utc_now_iso()}
    i += 1
    continue

5) No human_checkpoint context:
Inclua ctx.get("regions") quando o checkpoint for de regiões.
