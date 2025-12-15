from app.core.pipeline_engine import load_state, save_state

job_id = "00ae163c-a4ab-40b2-a984-2515b6d09146"
page_number = 1

print(f"Resetting typesetting for {job_id}")
state = load_state(job_id, page_number)

# Find index of typesetting
# We know it's at end, but let's be safe
if "typesetting" in state["steps"]:
    state["steps"]["typesetting"]["status"] = "pending"
    print("Set typesetting status to pending")

# Set current_step to 9 (Typesetting)
# Assuming 0-indexed: 
# 0 regions, 1 regions_human, 2 ocr, 3 grouping, 4 ocr_final, 5 ocr_human, 6 translation, 7 cleaning, 8 redraw, 9 typesetting.
state["current_step"] = 9
print("Set current_step to 9")

save_state(job_id, page_number, state)
print("State saved.")
