import sys
print("Checking imports...")
try:
    import pillow
    import PIL
    print(f"Pillow version: {PIL.__version__}")
except ImportError:
    print("Pillow import failed")

try:
    import manga_ocr
    print("manga_ocr import OK")
except ImportError as e:
    print(f"manga_ocr import FAILED: {e}")

try:
    from simple_lama_inpainting import SimpleLama
    print("SimpleLama import OK")
except ImportError as e:
    print(f"SimpleLama import FAILED: {e}")
