import logging
from pathlib import Path
from PIL import Image, ImageDraw

logger = logging.getLogger(__name__)

def cleaning_agent(image_path: Path, regions: dict) -> Image.Image:
    """
    Removes text from image by filling detected regions with specific color (Whiteout).
    Returns the PILLOW Image object (does not save).
    """
    try:
        img = Image.open(image_path).convert("RGB")
        draw = ImageDraw.Draw(img)
        
        region_list = regions.get("regions", [])
        if not region_list and "pages" in regions:
             # Handle structure where regions might be nested differently?
             # But typical regions file is { job_id, pages: [ {regions: []} ] } ?
             # No, regions_doc returned by region_agent is usually just dict with "regions" list if single page context,
             # OR it follows the pages structure.
             # Let's check region_agent.py or the actual saved json.
             # Based on previous files, it seems region_agent returns { "regions": [...] } for the page.
             pass

        # Robust extraction of region list
        target_regions = []
        if "regions" in regions and isinstance(regions["regions"], list):
            target_regions = regions["regions"]
        elif "pages" in regions:
            # Flatten regions from all pages found in the context
            # We assume the context might contain multiple pages, but we usually clean one image at a time.
            # Ideally we match page_number, but here we just grab all relative regions.
            # Since regions are usually tailored to the page in context.
            for p in regions["pages"]:
                if "regions" in p:
                    target_regions.extend(p["regions"])
             
        for r in target_regions:
            bbox = r.get("bbox")
            if not bbox:
                continue
            
            # shape: [x1, y1, x2, y2]
            x1, y1, x2, y2 = bbox
            
            # Check for Polygon first
            polygon = r.get("polygon")
            if polygon and isinstance(polygon, list) and len(polygon) > 2:
                # Expecting [[x,y], [x,y]...] from JSON
                # Erode the polygon by 3 pixels to avoid cleaning borders
                # We create a mask, draw the polygon, erode it, then paste white
                from PIL import ImageFilter
                
                mask = Image.new('L', img.size, 0)
                mask_draw = ImageDraw.Draw(mask)
                points = [tuple(p) for p in polygon]
                mask_draw.polygon(points, fill=255)
                
                # MinFilter(3) is 3x3 kernel -> roughly 1px erosion per pass, or 1.5px total radius?
                # Actually MinFilter(size) takes the min value in size x size box.
                # If we want 3px erosion (radius 3), we need size=7 (center pixel + 3 on each side).
                eroded_mask = mask.filter(ImageFilter.MinFilter(7))
                
                # Apply whiteout using eroded mask
                white_layer = Image.new('RGB', img.size, (255, 255, 255))
                img.paste(white_layer, (0, 0), eroded_mask)
            else:
                # Fallback to BBox
                # Draw rectangle (also erode slightly? BBox usually already tight or loose. Let's keep as is or erode 1px)
                # keeping standard behavior for bbox to avoid complex logic if not requested
                draw.rectangle([x1, y1, x2, y2], fill=(255, 255, 255), outline=None)
            
        return img
        
    except Exception as e:
        logger.error(f"Cleaning failed: {e}")
        # Return original on fail
        return Image.open(image_path).convert("RGB")
