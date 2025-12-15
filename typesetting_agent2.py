import logging
import base64
import json
import io
from pathlib import Path
from typing import Any, Dict, List, Optional
from PIL import Image, ImageDraw, ImageFont
import textwrap

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

4) Smart line breaks with syllable-respecting word splitting:
   - Prefer breaking lines at spaces.
   - If a single word must be split, split at a syllable boundary (best-effort for the given lang).
   - When splitting a word across lines, append an underscore "_" at the end of the first line segment to indicate continuation, and continue the remainder on the next line (no underscore at the beginning of the next line).
   - Never split in the middle of a syllable if avoidable.
   - For pt-BR best-effort heuristics:
     - Avoid breaking digraphs: "ch", "lh", "nh", "qu", "gu".
     - Prefer breaks between vowel/consonant groups (e.g., V-CV, VC-CV patterns).
     - Avoid leaving a single-letter fragment on a line unless unavoidable.

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
    # Assets are in backend/assets/fonts/
    # Resolved relative to running process usually works if CWD is backend
    
    font_files = {
        "dialogue": "comic-reg.ttf",
        "dialogue_bold": "comic.ttf", # We saved the Bold version as comic.ttf originally
        "shout": "comic.ttf", # Use bold for shout
        "square_box": "arial.ttf", # Fallback to system arial for narration
    }
    
    key = "dialogue"
    if category == "shout":
        key = "shout"
    elif category == "square_box":
        key = "square_box"
    elif is_bold:
        key = "dialogue_bold"
        
    filename = font_files.get(key, "comic-reg.ttf")
    
    # Try project assets first
    font_path = Path("assets/fonts") / filename
    
    if not font_path.exists():
        # Try finding system fonts if 'arial.ttf'
        if filename == "arial.ttf":
            try:
                return ImageFont.truetype("arial.ttf", size)
            except:
                pass
        # Fallback to default
        try:
            return ImageFont.load_default()
        except:
            pass
            
    try:
        return ImageFont.truetype(str(font_path), size)
    except:
        return ImageFont.load_default()

def wrap_text_hyphenated(text: str, font: ImageFont.FreeTypeFont, max_width: int):
    """
    Wraps text with hyphenation using Pyphen.
    Maximized for fitting.
    """
    # Fallback
    if not HAS_PYPHEN or not dic:
        try:
             # Estimate chars per line
             avg_char_w = font.getlength("a") * 0.95
             width_chars = int(max_width / avg_char_w)
             return textwrap.wrap(text, width=max(1, width_chars))
        except:
             return [text]

    words = text.split()
    lines = []
    current_line = []
    current_width = 0
    space_w = font.getlength(" ")
    
    for word in words:
        word_w = font.getlength(word)
        
        # If word fits, add it
        if current_width + word_w <= max_width:
            current_line.append(word)
            current_width += word_w + space_w
            continue
            
        # Word doesn't fit.
        # If line is empty, we MUST split the word or overflow.
        # If line is not empty, check if we can hyphenate to fit a piece on this line.
        
        # Try hyphenating
        try:
             hyphenated = dic.inserted(word) # e.g. "pa-la- vra"
             parts = hyphenated.split("-")
        except:
             parts = [word]
             
        if len(parts) == 1:
             # Cannot hyphenate
             if current_line:
                 lines.append(" ".join(current_line))
                 current_line = []
                 current_width = 0
             current_line.append(word)
             current_width = word_w + space_w
             continue
        
        # Try to pack parts
        
        # Find longest prefix that fits
        best_prefix = None
        best_suffix = None
        
        for i in range(len(parts)-1, 0, -1):
             prefix = "".join(parts[:i]) + "-"
             w = font.getlength(prefix)
             if current_width + w <= max_width:
                  best_prefix = prefix
                  best_suffix = "".join(parts[i:])
                  break
                  
        if best_prefix:
             current_line.append(best_prefix)
             lines.append(" ".join(current_line))
             current_line = []
             current_width = 0
             
             # Handle suffix logic (simplified: treat as new word)
             # Suffix might need further splitting? 
             # For simplicity, if suffix fits on new line, put it. Else overflow.
             current_line.append(best_suffix)
             current_width = font.getlength(best_suffix) + space_w
        else:
             # Even hyphenated start doesn't fit? Push to next line.
             if current_line:
                 lines.append(" ".join(current_line))
                 current_line = []
                 current_width = 0
             
             current_line.append(word)
             current_width = word_w + space_w
            
    if current_line:
        lines.append(" ".join(current_line))
        
    return lines

def typesetting_agent(base_image_path: Path, translation: dict, regions: dict, original_image_path: str = None, **kwargs) -> Image.Image:
    """
    Renders translated text onto the base image (Redraw/Cleaned).
    If original_image_path is provided, uses GPT-4o Vision to extract styles.
    """
    try:
        img = Image.open(base_image_path).convert("RGB")
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

        # 3. Render Loop
        for block in blocks:
            b_id = block.get("block_id")
            text = block.get("translation", "")
            
            if not text or not b_id:
                continue
                
            region = region_map.get(b_id)
            if region:
                bbox = region.get("bbox")
            else:
                bbox = block.get("bbox")
                
            if not bbox: continue
            
            x1, y1, x2, y2 = bbox
            rx, ry = x1, y1
            rw = x2 - x1
            rh = y2 - y1
            
            # --- Style Analysis ---
            # Defaults
            text_color = "#000000"
            stroke_color = "#FFFFFF"
            stroke_width = 3
            is_bold = False
            font_cat = "dialogue"
            
            if original_img:
                # Crop original
                crop = original_img.crop((x1, y1, x2, y2))
                # Crop Redraw (base) at same coords
                redraw_crop = img.crop((x1, y1, x2, y2))
                
                # Call AI with BOTH
                style = analyze_style_with_llm(crop, redraw_crop, text)
                text_color = style.get("text_color", "#000000")
                stroke_color = style.get("stroke_color", "#FFFFFF")
                stroke_width = int(style.get("stroke_width", 2))
                is_bold = style.get("is_bold", False)
                font_cat = style.get("font_category", "dialogue")
                
            # --- Text Fitting Logic ---
            max_size = 64
            min_size = 12
            optimal_font = None
            optimal_lines = []
            
            for size in range(max_size, min_size - 1, -2):
                font = get_font(size, font_cat, is_bold)
                
                # Use hyphenated wrapping
                lines = wrap_text_hyphenated(text, font, rw)
                
                # Verify Height
                line_height = size * 1.15
                total_h = len(lines) * line_height
                
                # Check width of each line (wrap_text should have handled it, but double check)
                valid_w = True
                for l in lines:
                    if font.getlength(l) > rw * 1.05: # 5% tolerance
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
            line_height = font.size * 1.15
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
