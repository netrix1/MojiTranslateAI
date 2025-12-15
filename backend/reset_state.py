from app.core.pipeline_engine import load_state, save_state
from app.core.config import settings
import sys

job_id = "00ae163c-a4ab-40b2-a984-2515b6d09146"
page_number = 1

print(f"Loading state for {job_id} page {page_number}")
state = load_state(job_id, page_number)
steps = state.get("steps", {})

# Check if steps exist
if "translation" in steps:
    print("Resetting translation status to pending")
    steps["translation"]["status"] = "pending"
    
if "typesetting" in steps:
    print("Resetting typesetting status to pending")
    steps["typesetting"]["status"] = "pending"
    
# Reset current step index to translation (Step 6 usually)
# Pipeline def: [regions, regions_human, ocr, grouping, human_chk, ocr_editor, translation, cleaning, typesetting]
# Index map: 0, 1, 2, 3, 4, 5, 6, 7, 8
# translation is index 6. 
state["current_step"] = 6
state["steps"] = steps

save_state(job_id, page_number, state)
print("State saved. Ready for re-run.")
