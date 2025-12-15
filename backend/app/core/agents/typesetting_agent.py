import logging
import base64
import json
import io
from pathlib import Path
from typing import Any, Dict, List, Optional
from PIL import Image, ImageDraw, ImageFont
import cv2
import numpy as np
import textwrap

# Pillow Compatibility
if hasattr(Image, "Resampling"):
    resample_bicubic = Image.Resampling.BICUBIC
else:
    resample_bicubic = Image.BICUBIC

# Local imports
from app.core.config import settings
from app.core.llm_client import get_llm_client

logger = logging.getLogger(__name__)
try:
    import pyphen
    dic = pyphen.Pyphen(lang='pt_BR')
    HAS_PYPHEN = True
except ImportError:
    HAS_PYPHEN = False
    dic = None

def encode_image_base64(img_crop: Image.Image) -> str:
    buffered = io.BytesIO()
    img_crop.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")

def analyze_style_with_llm(
    crop_img: Image.Image,
    redraw_crop: Image.Image,
    text: str,
    bbox_hint: Optional[List[int]] = None,
    lang: str = "pt-BR",
    reading_mode: str = "horizontal_ltr",
) -> Dict[str, Any]:
    """
    Usa GPT-4o Vision para extrair estilo + layout de texto a partir de:
    - ORIGINAL (crop com o texto original)
    - REDRAW (crop limpo/redraw, opcionalmente com máscara da área do balão).

    bbox_hint é apenas uma dica [x1, y1, x2, y2], NÃO o limite máximo do texto.
    O modelo deve usar principalmente o interior do balão no REDRAW.
    """

    def _extract_json(s: str) -> Dict[str, Any]:
        s = (s or "").strip()
        # tentativa direta
        try:
            obj = json.loads(s)
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass

        # fallback: primeira substring {...}
        m = re.search(r"\{[\s\S]*\}", s)
        if not m:
            return {}
        try:
            obj = json.loads(m.group(0))
            return obj if isinstance(obj, dict) else {}
        except Exception:
            return {}

    try:
        # estas funções precisam existir no seu código
        b64_orig = encode_image_base64(crop_img)
        b64_redraw = encode_image_base64(redraw_crop)

        bbox_hint_str = "null"
        if bbox_hint is not None:
            # garante formato [x1, y1, x2, y2]
            bbox_hint_str = str(list(bbox_hint))

        prompt = f"""
You are a manga/comic typesetting style + layout agent.

You will receive two images:
1) ORIGINAL: the original manga panel/bubble crop containing the original text (source language).
2) REDRAW: the same crop, already cleaned/redrawn, ready to receive text. In some cases, the REDRAW image may contain solid-colored filled regions (for example, green shapes) indicating the full interior area of each speech balloon / text box.

You will also receive:
- target_text: "{text}" (the translated text that must be placed into the REDRAW bubble)
- lang: "{lang}" (e.g. "pt-BR", "en", "ja")
- reading_mode: "{reading_mode}" one of ["horizontal_ltr","horizontal_rtl","vertical_ttb"] (default "horizontal_ltr")
- bbox_hint: {bbox_hint_str} as [x1, y1, x2, y2] in image coordinates, representing the approximate OCR bounding box of the original text for this block. This is a hint only, not a hard constraint.

Your job:
A) Infer the text visual style from ORIGINAL (font vibe, weight, stroke, colors).
B) Infer the usable bubble area from REDRAW and create a layout plan that fits target_text inside the balloon as naturally as possible, using bbox_hint only as a positional hint.

Key requirements:
1) Manga-like font selection:
   - Prefer fonts in this priority family list (use exact names as strings):
     ["armes","Laffayette Pro","Gargle","Blambot","Comicraft","Wild Words"]
   - Choose the best match per style category (dialogue/shout/box/handwritten). If none fits, still output the list above as fallback candidates in priority order.

2) Copy colors from ORIGINAL:
   - Output text_color (hex) and stroke_color (hex or null) that best match the original rendering.
   - If there is a stroke, estimate stroke_width in px (typical 2–4).

3) Bubble area vs bbox_hint:
   - Treat bbox_hint as an approximate anchor/center for this text block ONLY. It is not the maximum area for text.
   - Use the REDRAW image to infer the full interior area of the balloon or text box. If the REDRAW contains a filled mask region (for example, a solid green shape), interpret that region as the true maximum allowed area for the text.
   - You are allowed and encouraged to expand beyond bbox_hint to occupy the entire usable interior of the balloon, as long as the text stays clearly inside the balloon borders.
   - Only if the balloon contour or mask is ambiguous or missing, you may restrict yourself more closely to bbox_hint.

4) No word splitting:
   - Do NOT split words.
   - Do NOT use hyphens to break words across lines.
   - If a word is too long for a line, move the entire word to the next line.
   - Only split a word if it is longer than the entire width of the bubble (which is rare).
   - Prioritize keeping whole words together.

5) Natural manga composition:
   - Default alignment: center (unless ORIGINAL clearly uses left/right).
   - Respect ORIGINAL’s typical casing (ALL CAPS vs normal) if evident, but do not distort meaning.
   - Choose the largest readable font_size that fits comfortably into the inferred balloon area (not just bbox_hint).
   - Provide line_spacing and letter_spacing adjustments if needed to fit while preserving readability.
   - If the balloon is tall and narrow, favor more lines with shorter length; if it is wide, favor fewer lines with more characters.

6) Output must be JSON ONLY (no markdown, no extra text).

Return exactly one JSON object with this schema:

{{
  "font_category": "dialogue|shout|square_box|handwritten",
  "font_candidates_priority": ["..."],
  "chosen_font": "string",
  "is_bold": true/false,
  "is_italic": true/false,
  "text_color": "#RRGGBB",
  "stroke_color": "#RRGGBB" or null,
  "stroke_width": integer,
  "shadow": {{
    "enabled": true/false,
    "color": "#RRGGBB" or null,
    "offset_x": integer,
    "offset_y": integer,
    "blur": integer
  }},
  "layout": {{
    "reading_mode": "horizontal_ltr|horizontal_rtl|vertical_ttb",
    "safe_margin_ratio": number,
    "alignment": "center|left|right|justify",
    "rotation_degrees": number,
    "font_size_px": integer,
    "line_spacing_px": integer,
    "letter_spacing_px": integer,
    "text_lines": ["line1", "line2", "..."],
    "fit_confidence": 0.0 to 1.0,
    "notes": ["short note 1", "short note 2"]
  }}
}}

Fallback defaults if uncertain:
- font_category = "dialogue"
- chosen_font = "Wild Words"
- text_color = "#000000"
- stroke_color = "#FFFFFF"
- stroke_width = 3
- is_bold = false, is_italic = false
- alignment = "center"
- safe_margin_ratio = 0.06
- shadow disabled

Important: You must base style primarily on ORIGINAL, and the final usable area primarily on the REDRAW balloon interior (or mask). bbox_hint is only a positional hint and must never limit the maximum area if the balloon clearly extends beyond it. JSON ONLY.
""".strip()

        client = get_llm_client()
        if not client:
            logger.warning("No LLM client available for style analysis.")
            return {}

        # Exemplo com Chat Completions + visão.
        # Se estiver usando a Responses API, adapte esta parte.
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_orig}"}},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_redraw}"}},
                ],
            }],
            temperature=0.2,
        )

        raw_text = None
        if resp and getattr(resp, "choices", None):
            raw_text = resp.choices[0].message.content

        data = _extract_json(raw_text)
        if not isinstance(data, dict):
            logger.warning("LLM style/layout response is not a dict. raw=%r", raw_text)
            return {}

        return data

    except Exception as e:
        logger.exception("Style/layout analysis failed: %s", e)
        return {}


def get_font(size: int, category: str = "dialogue", is_bold: bool = False):
    """
    Selects font based on category and bold flag.
    """
    # Assets are in backend/assets/fonts/ or backend/fonts/
    
    font_files = {
        "dialogue": "Ames-Regular.otf", # User preference
        "dialogue_bold": "Ames-Regular.otf", # Fallback to Regular until we have Bold
        "shout": "comic.ttf", 
        "square_box": "arial.ttf", 
    }
    
    key = "dialogue"
    if category == "shout":
        key = "shout"
    elif category == "square_box":
        key = "square_box"
    elif is_bold:
        key = "dialogue_bold"
        
    filename = font_files.get(key, "Ames-Regular.otf")
    
    # Search paths
    search_paths = [
        Path("fonts"),           # backend/fonts
        Path("assets/fonts"),    # backend/assets/fonts
    ]
    
    font_path = None
    for p in search_paths:
        candidate = p / filename
        if candidate.exists():
            font_path = candidate
            break
    
    if not font_path:
        # Try finding system fonts if 'arial.ttf'
        if filename == "arial.ttf":
            try:
                return ImageFont.truetype("arial.ttf", size)
            except:
                pass
        # Fallback
        try:
            return ImageFont.load_default()
        except:
             # Fallback to whatever is available if Ames is missing?
             # Try comic-reg as last resort inside assets?
             fallback = Path("assets/fonts/comic-reg.ttf")
             if fallback.exists():
                 return ImageFont.truetype(str(fallback), size)
             return ImageFont.load_default()
            
    try:
        return ImageFont.truetype(str(font_path), size)
    except:
        return ImageFont.load_default()

def detect_balloon_contour(pil_img: Image.Image, center_point: tuple) -> Optional[tuple]:
    """
    Tries to detect the balloon area starting from center_point (x, y).
    Returns (x, y, w, h) or None if detection fails/is invalid.
    """
    try:
        # Convert to CV2
        cv_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        h, w = cv_img.shape[:2]
        
        cx, cy = int(center_point[0]), int(center_point[1])
        
        if cx < 0 or cx >= w or cy < 0 or cy >= h:
            return None
            
        # Create mask for floodFill (h+2, w+2)
        mask = np.zeros((h + 2, w + 2), np.uint8)
        
        # floodFill
        # loDiff/upDiff = tolerance for color similarity. 
        # Using a small tolerance assuming balloon background is relatively solid.
        flags = 4 | (255 << 8) | cv2.FLOODFILL_FIXED_RANGE | cv2.FLOODFILL_MASK_ONLY
        cv2.floodFill(cv_img, mask, (cx, cy), (0, 0, 0), (5, 5, 5), (5, 5, 5), flags)
        
        # Get bounding rect of the mask
        # Mask include 1 px border, so strict crop is [1:-1, 1:-1]
        mask_roi = mask[1:-1, 1:-1]
        
        # --- Morphological Opening to remove tails ---
        # Structure element size: generous enough to cut thin tails (~13px)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (13, 13))
        opened_mask = cv2.morphologyEx(mask_roi, cv2.MORPH_OPEN, kernel)
        
        points = cv2.findNonZero(opened_mask)
        
        # Fallback: if opening removed everything (balloon too small?), use original mask
        if points is None:
             points = cv2.findNonZero(mask_roi)
             
        if points is None:
            return None
            
        bx, by, bw, bh = cv2.boundingRect(points)
        
        # Validation
        # If too small, ignore
        if bw < 20 or bh < 20: 
            return None
            
        # If basically the whole image, ignore (floodfill leaked everywhere)
        if bw > w * 0.95 and bh > h * 0.95:
             return None
             
        return (bx, by, bw, bh)
        
    except Exception as e:
        logger.warning(f"Balloon detection error: {e}")
        return None

def wrap_text_hyphenated(text: str, font: ImageFont.FreeTypeFont, max_width: int):
    """
    Wraps text WITHOUT hyphenation, respecting explicit newlines.
    """
    # Split into paragraphs to preserve user's explicit newlines
    paragraphs = text.split('\n')
    final_lines = []
    
    space_w = font.getlength(" ")
    
    for paragraph in paragraphs:
        words = paragraph.split()
        if not words:
            # Empty paragraph means empty line
            final_lines.append("")
            continue

        current_line = []
        current_width = 0
        
        for word in words:
            word_w = font.getlength(word)
            
            # Check if adding this word exceeds max_width
            # (current_width includes spaces for existing words)
            if current_line:
                 new_width = current_width + space_w + word_w
            else:
                 new_width = word_w
                 
            if new_width <= max_width:
                 current_line.append(word)
                 current_width = new_width
            else:
                 # Line full, push current line
                 if current_line:
                     final_lines.append(" ".join(current_line))
                 
                 # Start new line with this word
                 current_line = [word]
                 current_width = word_w
                 
        # Append last line of paragraph
        if current_line:
            final_lines.append(" ".join(current_line))
            
    return final_lines


def create_mask_from_polygon(polygon: List[List[int]], width: int, height: int) -> np.ndarray:
    """Creates a binary mask (0/255) from a list of points [[x,y], ...]."""
    mask = np.zeros((height, width), dtype=np.uint8)
    pts = np.array(polygon, np.int32)
    pts = pts.reshape((-1, 1, 2))
    cv2.fillPoly(mask, [pts], 255)
    
    # Erode mask to provide safety margin (prevent text touching edges)
    # INCREASED Erosion to 11x11 (~5px radius)
    kernel = np.ones((11, 11), np.uint8) 
    mask = cv2.erode(mask, kernel, iterations=1)
    
    return mask

def wrap_text_to_mask(text: str, font: ImageFont.FreeTypeFont, mask: np.ndarray, start_y: int, text_height_px: int, stroke_width: int = 4) -> List[tuple]:
    """
    Wraps text ensuring every pixel of the text (+stroke) falls into white mask area.
    """
    lines_with_pos = []
    
    words = text.split()
    if not words: 
        return []

    space_w = font.getlength(" ")
    h, w = mask.shape
    
    current_y = start_y
    idx = 0
    
    # Pre-calculate inverted mask for fast collision check
    # mask is 255 (valid), 0 (invalid)
    # inverted: 255 (invalid), 0 (valid)
    inverted_mask = cv2.bitwise_not(mask)
    
    # DEBUG: Save masks for the FIRST call only (heuristic)
    import os
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    debug_dir = os.path.join(base_dir, "debug_output")
    os.makedirs(debug_dir, exist_ok=True)
    
    # Save only if specific flag file doesn't exist to prevent spam
    debug_mask_path = os.path.join(debug_dir, "debug_mask_last.png")
    debug_inv_path = os.path.join(debug_dir, "debug_inverted_last.png")
    
    Image.fromarray(mask).save(debug_mask_path)
    Image.fromarray(inverted_mask).save(debug_inv_path)

    def check_text_collision(text_line, dx, dy):
        """
        Renders text to a temp mask, dilates it, and checks overlap with inverted_mask.
        Returns True if collision detected.
        """
        # 1. Create temp image for text
        # Size: enough to hold the text line.
        # We need exact dimensions.
        try:
            # Use 'lt' anchor to match drawing
            bbox = font.getbbox(text_line, anchor='lt') 
            # bbox is (left, top, right, bottom)
            # Width/Height of ink
            bw = bbox[2] - bbox[0]
            bh = bbox[3] - bbox[1]
        except:
             bw, bh = font.getsize(text_line)
             bbox = (0, 0, bw, bh)
             
        # ROI Size
        # We draw at (dx, dy).
        # But we need to handle the whole area including stroke.
        # Let's create a temp canvas of safe size, e.g. text size + padding
        
        # ROI approach:
        # Determine ROI on main mask.
        
        # Draw position is (dx, dy). 
        # Text ink goes from (dx+bbox[0], dy+bbox[1]) to (dx+bbox[2], dy+bbox[3])
        # Add stroke/padding
        # INCREASED PADDING TO 4
        pad = stroke_width + 4
        
        x1 = int(dx + bbox[0] - pad)
        y1 = int(dy + bbox[1] - pad)
        x2 = int(dx + bbox[2] + pad)
        y2 = int(dy + bbox[3] + pad)
        
        # Clip to image bounds
        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = min(w, x2)
        y2 = min(h, y2)
        
        if x2 <= x1 or y2 <= y1: return True # Invalid geometry? or just disjoint? 
        
        # Extract invalid zone ROI
        roi_invalid = inverted_mask[y1:y2, x1:x2]
        
        # Create text mask for this ROI
        # We need to draw the text relative to x1, y1
        roi_w = x2 - x1
        roi_h = y2 - y1
        
        txt_img = Image.new('L', (roi_w, roi_h), 0)
        d = ImageDraw.Draw(txt_img)
        
        # Draw text using 'lt' anchor
        # Text is drawn at (dx, dy) in absolute coords.
        # In ROI coords: (dx - x1, dy - y1)
        d.text((dx - x1, dy - y1), text_line, font=font, fill=255, anchor='lt')
        
        txt_arr = np.array(txt_img)
        
        # Dilate text mask (simulate stroke + safety margin)
        # Dilate by pad size
        kernel_size = pad * 2 + 1 
        kernel = np.ones((kernel_size, kernel_size), np.uint8)
        dilated_txt = cv2.dilate(txt_arr, kernel, iterations=1)
        
        # Check intersection
        collision = cv2.bitwise_and(dilated_txt, roi_invalid)
        
        return np.max(collision) > 0

    while idx < len(words):
        # ... existing generic scan logic ...
        # (Assuming scan logic finds available_width and x_min correctly)
        
        # ... [Scan Lines Code Skipped, assume it is identical to previous block] ...
        
        # Just update the inner word loop and checking
        # But wait, replacing the whole loop is safer to ensure variables match.
        pass # Placeholder for replace logic logic


    while idx < len(words):
        # ... logic ...
        # Instead of generic row scan, we rely entirely on check_fit or improved scan.
        # But we still need an initial X.
        # Let's keep the intersection logic to find *candidates*, then validate.
        
        # ... (keep scan logic for optimization) ...
        # (Top/Bottom check is good heuristic to start)
        sample_y_bottom = min(h - 1, current_y + text_height_px + stroke_width) # include stroke
        
        # Ensure we are checking rows including the stroke padding top/bottom
        # For simplicity, stick to current_y and bottom.
        
        row_top = mask[current_y, :]
        row_bot = mask[sample_y_bottom, :]
        
        if np.max(row_top) == 0 or np.max(row_bot) == 0:
             current_y += text_height_px
             if current_y >= h: break
             continue
             
        white_top = np.where(row_top > 0)[0]
        white_bot = np.where(row_bot > 0)[0]
        
        if len(white_top) == 0 or len(white_bot) == 0:
            current_y += text_height_px
            if current_y >= h: break
            continue
            
        t_x1, t_x2 = white_top[0], white_top[-1]
        b_x1, b_x2 = white_bot[0], white_bot[-1]
        
        x_min = max(t_x1, b_x1) + stroke_width # Safety margin
        x_max = min(t_x2, b_x2) - stroke_width
        
        if x_min >= x_max:
             current_y += text_height_px
             continue
             
        available_width = x_max - x_min
        
        # Apply margin (simulated) - FORCE MARGIN to prevent edge leakage
        # 5% each side + 4px absolute
        margin_px = int(available_width * 0.05) + 4
        
        # Shrink available area
        x_start_real = x_min + margin_px
        x_end_real = x_max - margin_px
        
        if x_end_real <= x_start_real:
             current_y += text_height_px
             continue
             
        available_width = x_end_real - x_start_real
        x_min = x_start_real # Update for centering logic
        x_max = x_end_real
        
        # Fit words
        line_words = []
        current_w = 0
        
        while idx < len(words):
            word = words[idx]
            word_w = font.getlength(word)
            
            # Tentative width
            test_w = current_w + (space_w if line_words else 0) + word_w
            
            if test_w <= available_width:
                 # Check Fit with Bitmap Collision
                 line_text_candidate = " ".join(line_words + [word])
                 
                 center_x = x_min + available_width / 2
                 draw_x = center_x - test_w / 2
                 
                 if not check_text_collision(line_text_candidate, draw_x, current_y):
                     # Fits!
                     if line_words: current_w += space_w
                     current_w += word_w
                     line_words.append(word)
                     idx += 1
                 else:
                     # Collides
                     if not line_words: break 
                     else: break
            else:
                 break
                 
        if line_words:
             line_text = " ".join(line_words)
             center_x = x_min + (x_max - x_min) / 2
             text_w = font.getlength(line_text)
             draw_x = center_x - text_w / 2
             lines_with_pos.append((line_text, draw_x, current_y))
             current_y += text_height_px
        else:
             current_y += text_height_px

    return lines_with_pos


def typesetting_agent(base_image_path: Path, translation: dict, regions: dict, original_image_path: str = None, **kwargs) -> Image.Image:
    """
    Renders translated text onto the base image (Redraw/Cleaned).
    If original_image_path is provided, uses GPT-4o Vision to extract styles.
    """
    try:
        img = Image.open(base_image_path).convert("RGB")
        
        # --- DEBUG INPUTS ---
        print(f"DEBUG: Typesetting Agent Started.")
        
        print(f"DEBUG: Translation type: {type(translation)}")
        
        # Normalize Regions
        region_list_debug = []
        if isinstance(regions, dict):
             region_list_debug = list(regions.values())
        elif isinstance(regions, list):
             region_list_debug = regions
             
        print(f"DEBUG: Regions count: {len(region_list_debug)}")
        if region_list_debug:
            first_reg = region_list_debug[0]
            print(f"DEBUG: Sample region type: {type(first_reg)}")
            if isinstance(first_reg, dict):
                print(f"DEBUG: Sample region keys: {first_reg.keys()}")
                if 'polygon' in first_reg:
                     print(f"DEBUG: Sample region polygon points: {len(first_reg['polygon'])}")
                else:
                     print("DEBUG: No 'polygon' key in first region.")
            else:
                print(f"DEBUG: Sample region content: {first_reg}")
                
        # --------------------
        
        draw = ImageDraw.Draw(img)
        width, height = img.size
        
        # Load original for analysis
        original_img = None
        if original_image_path and Path(original_image_path).exists():
            original_img = Image.open(original_image_path).convert("RGB")
        
        # 1. Normalize Regions Input
        if "regions" in regions and isinstance(regions["regions"], list):
            region_list = regions["regions"]
        elif "pages" in regions:
            region_list = []
            for p in regions["pages"]:
                if "regions" in p:
                    region_list.extend(p["regions"])
        elif isinstance(regions, list):
            region_list = regions
        else:
            region_list = []
        
        region_map = {r["region_id"]: r for r in region_list if "region_id" in r}

        # 2. Normalize Translation Input
        blocks = []
        if "pages" in translation:
            for p in translation["pages"]:
                blocks.extend(p.get("blocks", []))
        elif "blocks" in translation:
            blocks = translation["blocks"]
        elif isinstance(translation, list):
             blocks = translation

        # --- DEBUG: Visualize Polygons ---
        try:
            debug_img = img.copy().convert("RGBA")
            debug_draw = ImageDraw.Draw(debug_img, "RGBA")
            has_polys = False
            
            # Collect all polygons
            all_polys = []
            
            # From regions
            for r in region_list:
                if isinstance(r, dict):
                    poly = r.get("polygon")
                    if poly and len(poly) > 2:
                        all_polys.append(poly)
            
            # From blocks (if regions missing)
            for b in blocks:
                if isinstance(b, dict):
                    poly = b.get("polygon")
                    if poly and len(poly) > 2:
                         all_polys.append(poly)
                     
            for poly in all_polys:
                pts = [tuple(p) for p in poly]
                debug_draw.polygon(pts, fill=(255, 0, 0, 128), outline=(255, 0, 0, 255))
                has_polys = True
            
            print(f"DEBUG: Found {len(all_polys)} polygons to visualize.")
            
            if has_polys:
                import os
                base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
                debug_dir = os.path.join(base_dir, "debug_output")
                os.makedirs(debug_dir, exist_ok=True)
                save_path = os.path.join(debug_dir, "debug_polygons.png")
                debug_img.save(save_path)
                print(f"DEBUG: Saved polygon visualization to {save_path}")
        except Exception as e:
            print(f"DEBUG: Failed to save debug image: {e}")
        # ---------------------------------

        # 3. Render Loop
        # DISABLED by User Request: Static result is no longer needed/wanted.
        # Iterating over empty list to skip rendering without changing indentation of the huge block below.
        for block in ([]): 
            b_id = block.get("block_id")
            text = block.get("translation", "")
            
            if not text or not b_id:
                continue
                
            region = region_map.get(b_id)
            if region:
                bbox = region.get("bbox")
                polygon = region.get("polygon") # expecting list of [x,y]
            else:
                bbox = block.get("bbox")
                polygon = block.get("polygon")
                
            if not bbox and not polygon: continue
            
            # --- Style Analysis (Simplified for this snippet) ---
            # Defaults
            text_color = "#000000"
            stroke_color = "#FFFFFF"
            stroke_width = 3
            is_bold = False
            font_cat = "dialogue"
            
            # Check for Manual Style Override
            manual_style = block.get("rendering_style")
            
            # If no manual style, but original image exists, try AI
            if not manual_style and original_img and bbox:
                x1, y1, x2, y2 = bbox
                crop = original_img.crop((x1, y1, x2, y2))
                redraw_crop = img.crop((x1, y1, x2, y2))
                style = analyze_style_with_llm(crop, redraw_crop, text)
                text_color = style.get("text_color", "#000000")
                stroke_color = style.get("stroke_color", "#FFFFFF")
                stroke_width = int(style.get("stroke_width", 2))
                is_bold = style.get("is_bold", False)
                font_cat = style.get("font_category", "dialogue")
            
            # Apply Manual Style Overrides if present
            if manual_style:
                # If values are set, use them.
                if manual_style.get("text_color"): text_color = manual_style["text_color"]
                if manual_style.get("stroke_color"): stroke_color = manual_style["stroke_color"]
                if "stroke_width" in manual_style: stroke_width = int(manual_style["stroke_width"])
                if "is_bold" in manual_style: is_bold = manual_style["is_bold"]
                if manual_style.get("font_family"): font_cat = manual_style["font_family"]

            # --- Text Fitting Logic ---
            
            # MODE A: Polygon (Manual)
            if polygon and len(polygon) > 2:
                 # Create Mask
                 pts = np.array(polygon)
                 
                 # Apply Box Scaling if requested
                 if manual_style and manual_style.get("box_scale"):
                     scale = float(manual_style["box_scale"])
                     if scale != 1.0:
                         # Calculate Centroid
                         centroid = pts.mean(axis=0)
                         # Scale points relative to centroid
                         pts = centroid + (pts - centroid) * scale
                         polygon = pts.astype(int).tolist() # Update polygon for drawing/mask
                         pts = np.array(polygon) # Update pts for bbox calc below

                 mask = create_mask_from_polygon(polygon, width, height)
                 
                 # Find bounding box of polygon for basic stats
                 pts = np.array(polygon)
                 x_min, y_min = pts.min(axis=0)
                 x_max, y_max = pts.max(axis=0)
                 
                 # Try fonts
                 max_size = 64
                 min_size = 12
                 optimal_font = None
                 optimal_layout = [] # list of (text, x, y)
                 
                 # Manual Font Size Override
                 manual_size_scale = manual_style.get("font_size") if manual_style else None
                 if manual_size_scale:
                     # Calculate exact pixel size
                     # Scale 1-10 means 1% to 10% of image width
                     size = int(width * (float(manual_size_scale) / 100.0))
                     size = max(8, size) # Minimum safety
                     
                     print(f"DEBUG: Using Manual Font Size: {manual_size_scale}% -> {size}px")
                     
                     font = get_font(size, font_cat, is_bold)
                     line_height = int(size * 1.1)
                     
                     # Force wrap with this size. 
                     # We still try to center it if it fits, or just place it at top.
                     initial_y = int(y_min)
                     layout = wrap_text_to_mask(text, font, mask, initial_y, line_height)
                     
                     # Simple Centering Attempt
                     if layout:
                        used_h = len(layout) * line_height
                        poly_h = y_max - y_min
                        if used_h < poly_h:
                            center_y = int(y_min + (poly_h - used_h) / 2)
                            center_y = max(int(y_min), center_y)
                            layout_centered = wrap_text_to_mask(text, font, mask, center_y, line_height)
                            if layout_centered:
                                layout = layout_centered
                     
                     optimal_font = font
                     optimal_layout = layout
                     
                 else:
                     # Auto-Sizing Loop
                     for size in range(max_size, min_size - 1, -2):
                         font = get_font(size, font_cat, is_bold)
                         line_height = int(size * 1.1)
                     
                         # Pass 1: Attempt wrap at top to gauge height
                         # Start slightly below y_min to avoid grazing top edge
                         initial_y = int(y_min)
                         layout_pass1 = wrap_text_to_mask(text, font, mask, initial_y, line_height)
                         
                         # Determine used height
                         if not layout_pass1: 
                             continue
                             
                         # Check fit roughly (count characters)
                         rendered_chars = len("".join([l[0] for l in layout_pass1]).replace(" ", ""))
                         target_chars = len(text.replace(" ", ""))
                         
                         # Simple check: if we lost > 20% of chars, it definitely didn't fit well at top
                         # But main goal is to find height.
                         used_h = len(layout_pass1) * line_height
                         poly_h = y_max - y_min
                         
                         # Pass 2: Re-wrap at calculated center
                         if used_h < poly_h:
                             center_y = int(y_min + (poly_h - used_h) / 2)
                             # Clamp start_y
                             center_y = max(int(y_min), center_y)
                             
                             layout_pass2 = wrap_text_to_mask(text, font, mask, center_y, line_height)
                             
                             # STRICT CHECK: Did we fit EVERYTHING?
                             rendered_text_2 = " ".join([l[0] for l in layout_pass2])
                             # Comparison ignoring spaces
                             if len(rendered_text_2.replace(" ", "")) >= target_chars:
                                  # Fits perfectly centered!
                                  optimal_font = font
                                  optimal_layout = layout_pass2
                                  break
                         
                         # If Pass 1 fit perfectly and we didn't center (e.g. strict top?), maybe use it?
                         # But we prefer centering. If Pass 2 failed, maybe font is too big for the narrow center.
                         # Continue loop to shrink font.
                     
                 if not optimal_layout:
                      # Fallback: strict fit failed.
                      # Use smallest font at center or top?
                      optimal_font = get_font(min_size, font_cat, is_bold)
                      # Try centering with smallest
                      # Estimate height: chars / (width/size) lines... hard.
                      # Just put at top
                      optimal_layout = wrap_text_to_mask(text, optimal_font, mask, int(y_min), int(min_size*1.1))

                 # Draw
                 font = optimal_font
                 
                 angle = int(manual_style.get("angle", 0)) if manual_style else 0
                 
                 if angle != 0 and optimal_layout:
                     # ROTATION LOGIC
                     # 1. Calculate Text Block Bounds
                     min_lx = min([l[1] for l in optimal_layout])
                     max_lx = max([l[1] + font.getlength(l[0]) for l in optimal_layout])
                     min_ly = min([l[2] for l in optimal_layout])
                     # height of last line
                     last_line_y = optimal_layout[-1][2]
                     # approximate height using getbbox or simple logic
                     try:
                         lb = font.getbbox(optimal_layout[-1][0], anchor='lt')
                         last_h = lb[3] - lb[1]
                     except:
                         last_h = int(manual_style.get("font_size", 12)) if manual_style else 12 # Fallback
                     max_ly = last_line_y + last_h
                     
                     text_w = int(max_lx - min_lx + 20)
                     text_h = int(max_ly - min_ly + 20)
                     
                     # 2. Render to temp transparent image
                     txt_layer = Image.new('RGBA', (text_w, text_h), (0,0,0,0))
                     txt_draw = ImageDraw.Draw(txt_layer)
                     
                     for line_text, lx, ly in optimal_layout:
                         # Relocate to (0,0) of temp layer
                         rel_x = lx - min_lx + 10
                         rel_y = ly - min_ly + 10
                         
                         if stroke_color:
                             txt_draw.text((rel_x, rel_y), line_text, font=font, fill=stroke_color, stroke_width=stroke_width, stroke_fill=stroke_color, anchor='lt')
                         txt_draw.text((rel_x, rel_y), line_text, font=font, fill=text_color, anchor='lt')
                         
                     # 3. Rotate
                     if angle != 0:
                         # Negative angle because PIL rotates counter-clockwise?
                         # Usually 90 is CCW. StyleEditor -180..180.
                         # Let's assume standard behavior.
                         txt_layer = txt_layer.rotate(angle, expand=True, resample=resample_bicubic)
                     
                     # 4. Paste back centered at original centroid
                     orig_cx = min_lx + (max_lx - min_lx) / 2
                     orig_cy = min_ly + (max_ly - min_ly) / 2
                     
                     new_w, new_h = txt_layer.size
                     paste_x = int(orig_cx - new_w / 2)
                     paste_y = int(orig_cy - new_h / 2)
                     
                     img.paste(txt_layer, (paste_x, paste_y), txt_layer)
                     
                 else:
                     # STANDARD DRAWING
                     for line_text, lx, ly in optimal_layout:
                          if stroke_color:
                              draw.text((lx, ly), line_text, font=font, fill=stroke_color, stroke_width=stroke_width, stroke_fill=stroke_color, anchor='lt')
                          draw.text((lx, ly), line_text, font=font, fill=text_color, anchor='lt')
                      
                 continue # Skip standard logic
            
            # MODE B: Standard BBox (Fallback if no polygon)
            if not bbox: continue
            
            x1, y1, x2, y2 = bbox
            
            # --- AUTO BALLOON DETECTION DISABLED (User Request) ---
            # balloon_rect = detect_balloon_contour(img, (cx, cy))
            # Fallback to Inflated Bbox only
            
            w_orig = x2 - x1
            h_orig = y2 - y1
            cx = x1 + w_orig / 2
            cy = y1 + h_orig / 2
            
            pad_ratio = 0.15
            w_new = w_orig * (1.0 + pad_ratio * 2)
            h_new = h_orig * (1.0 + pad_ratio * 2)
            
            rx = cx - w_new / 2
            ry = cy - h_new / 2
            rw = w_new
            rh = h_new

            # --- Text Fitting Logic (Standard Rect) ---
            max_size = 64
            min_size = 12
            optimal_font = None
            optimal_lines = []
            
            for size in range(max_size, min_size - 1, -2):
                font = get_font(size, font_cat, is_bold)
                
                # Use standard wrap (no hyphen)
                lines = wrap_text_hyphenated(text, font, rw)
                
                # Verify Height
                line_height = size * 1.10 
                total_h = len(lines) * line_height
                
                valid_w = True
                for l in lines:
                    if font.getlength(l) > rw * 1.05: 
                        valid_w = False
                        break
                
                if valid_w and total_h <= rh:
                    optimal_font = font
                    optimal_lines = lines
                    break
            
            if not optimal_font:
                optimal_font = get_font(min_size, font_cat, is_bold)
                optimal_lines = wrap_text_hyphenated(text, optimal_font, rw)

            # --- Drawing ---
            font = optimal_font
            line_height = font.size * 1.10
            total_text_h = len(optimal_lines) * line_height
            
            # Vertical Center
            y = ry + (rh - total_text_h) / 2
            
            for line in optimal_lines:
                try:
                    w = font.getlength(line)
                except:
                    w = 0
                
                # Horizontal Center
                x = rx + (rw - w) / 2
                
                # Draw Stroke
                if stroke_color:
                    draw.text((x, y), line, font=font, fill=stroke_color, stroke_width=stroke_width, stroke_fill=stroke_color)
                
                # Draw Text
                draw.text((x, y), line, font=font, fill=text_color)
                
                y += line_height
                
        return img
        
    except Exception as e:
        import traceback
        logger.error(f"Typesetting failed: {e}")
        logger.error(f"traceback: {traceback.format_exc()}")
        return Image.open(base_image_path).convert("RGB")
