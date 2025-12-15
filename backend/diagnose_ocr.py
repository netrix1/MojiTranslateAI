
import sys
import os
import traceback
from pathlib import Path

# Add backend to path
sys.path.insert(0, os.getcwd())

# Setup logging manually
log_file = Path("ocr_error.log")

def log(msg):
    print(msg)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

log("Starting OCR Diagnosis...")

try:
    log("Importing app.ocr.mangaocr_tool...")
    from app.ocr.mangaocr_tool import run_ocr_mangaocr, _get_ocr
    log("Import successful.")
except Exception as e:
    log("[FATAL] Import failed:")
    log(traceback.format_exc())
    sys.exit(1)

try:
    log("Initializing MangaOCR model...")
    _get_ocr()
    log("Model initialized.")
except Exception as e:
    log("[FATAL] Model initialization failed:")
    log(traceback.format_exc())
    sys.exit(1)

# Create a dummy image unconditionally
from PIL import Image, ImageDraw
dummy_path = Path("dummy.jpg")
img = Image.new('RGB', (500, 500), color = 'white')
d = ImageDraw.Draw(img)
d.text((10,10), "Hello World", fill=(0,0,0))
img.save(dummy_path)
log(f"Created dummy image at {dummy_path.absolute()}")
test_img = dummy_path

try:
    log("Running run_ocr_mangaocr...")
    # Mock regions
    regions = {
        "pages": [{
            "page_number": 1,
            "regions": [{"bbox": [10, 10, 100, 100], "type_hint": "speech"}]
        }]
    }
    
    res = run_ocr_mangaocr(
        image_path=str(test_img.absolute()),
        page_number=1,
        regions=regions
    )
    log("Success! Result:")
    log(str(res))
    
except Exception as e:
    log("[FATAL] Execution failed:")
    log(traceback.format_exc())
    
log("Diagnosis complete.")
