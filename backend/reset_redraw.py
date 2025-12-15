from app.core.pipeline_engine import load_state, save_state
import sys

job_id = "00ae163c-a4ab-40b2-a984-2515b6d09146"
page_number = 1

print(f"Loading state for {job_id} page {page_number}")
state = load_state(job_id, page_number)
steps = state.get("steps", {})

# Clear status for relevant steps
for s in ["cleaning", "redraw", "typesetting"]:
    if s in steps:
        print(f"Resetting {s} status to pending")
        steps[s]["status"] = "pending"
    else:
        print(f"Step {s} not found in state, which is expected for new step 'redraw'")

# Assuming pipeline order: 
# ... translation (6), cleaning (7), redraw (8), typesetting (9)
# We want to restart from cleaning to be safe, or just redraw (8).
# Safest is cleaning (7) so we guarantee the input to redraw is fresh?
# Actually input to redraw is original image + regions. Cleaning is separate.
# But Redraw is step 8.
# Let's set current step to 8 (Redraw).
state["current_step"] = 8 # Index 8 is Redraw

state["steps"] = steps
save_state(job_id, page_number, state)
print("State saved. Set current_step=8 (Redraw). Statuses cleared.")
