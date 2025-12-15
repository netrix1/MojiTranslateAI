import os
from pathlib import Path

job_dir = Path("/home/netrix/projects/MojiTranslateAI/data/jobs/00ae163c-a4ab-40b2-a984-2515b6d09146")

print(f"Listing files in {job_dir}:")
if not job_dir.exists():
    print("Job dir not found!")
else:
    for root, dirs, files in os.walk(job_dir):
        level = root.replace(str(job_dir), '').count(os.sep)
        indent = ' ' * 4 * (level)
        print(f"{indent}{os.path.basename(root)}/")
        subindent = ' ' * 4 * (level + 1)
        for f in files:
            p = Path(root) / f
            print(f"{subindent}{f} ({p.stat().st_size} bytes)")
