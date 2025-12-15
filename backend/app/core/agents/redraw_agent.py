import logging
from pathlib import Path
from PIL import Image, ImageDraw
from simple_lama_inpainting import SimpleLama

logger = logging.getLogger(__name__)

# Initialize model lazily or globally? 
# For now, local init might re-load model every time. 
# Better to init outside if possible, but let's keep it simple first.
_lama = None

def get_lama():
    global _lama
    if _lama is None:
        logger.info("Initializing SimpleLama model...")
        _lama = SimpleLama()
    return _lama

def redraw_agent(image_path: Path, regions: dict) -> Image.Image:
    """
    Uses LaMa (Large Mask Inpainting) to restore background in regions where text is present.
    Takes original image and in-paints the regions defined by bounding boxes.
    """
    try:
        # Load Original Image
        img = Image.open(image_path).convert("RGB")
        w, h = img.size
        
        # Create Mask
        # precise mask is needed. 0=Background, 255=Mask to inpaint
        mask = Image.new("L", (w, h), 0)
        draw = ImageDraw.Draw(mask)
        
        # Extract regions matching cleaning agent logic
        target_regions = []
        if "regions" in regions and isinstance(regions["regions"], list):
            target_regions = regions["regions"]
        elif "pages" in regions:
            for p in regions["pages"]:
                if "regions" in p:
                    target_regions.extend(p["regions"])
        elif isinstance(regions, list):
             target_regions = regions
             
        # Draw regions onto mask
        count = 0
        for r in target_regions:
            # Check for Polygon first
            polygon = r.get("polygon")
            
            if polygon and isinstance(polygon, list) and len(polygon) > 2:
                # Use strict polygon for redraw as requested
                points = [tuple(p) for p in polygon]
                draw.polygon(points, fill=255)
                count += 1
            else:
                bbox = r.get("bbox")
                if not bbox: continue
                
                # [x1, y1, x2, y2]
                x1, y1, x2, y2 = bbox
                
                # Draw white rectangle on mask
                draw.rectangle([x1, y1, x2, y2], fill=255)
                count += 1
            
        if count == 0:
            logger.info("No regions to redraw, returning original.")
            return img

        # Dilate mask? 
        # LaMa is good with large masks, but dilating slightly helps cover edges of compression artifacts
        # We can use PIL ImageFilter or just assume bbox is generous enough.
        # Let's trust the bbox for now, or maybe expand by 2px?
        # Manually expand bbox in drawing loop is easier.
        
        # Run Inpainting
        lama = get_lama()
        result = lama(img, mask)
        
        return result
        
    except Exception as e:
        logger.error(f"Redraw (LaMa) failed: {e}")
        # Fallback to original
        return Image.open(image_path).convert("RGB")
