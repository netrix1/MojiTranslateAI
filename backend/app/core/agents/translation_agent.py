from app.core.storage import read_json
from app.core.llm_client import translate_text

def translation_agent(ocr_final: dict) -> dict:
    """
    Real translation agent using LLM.
    Takes ocr_final structure and creates a translation structure.
    """
    translated_pages = []
    
    for page in ocr_final.get("pages", []):
        t_blocks = []
        for block in page.get("blocks", []):
            original = block.get("text") or block.get("original_text") or ""
            
            # Skip empty or very short noise
            if not original.strip() or len(original) < 2:
                 translation = original
            else:
                 translation = translate_text(original)

            t_blocks.append({
                "block_id": block.get("block_id"),
                "region_id": block.get("region_id"),
                "bbox": block.get("bbox"),
                "original": original,
                "translation": translation,
                "notes": "LLM-Translated"
            })
            
        translated_pages.append({
            "page_number": page.get("page_number"),
            "blocks": t_blocks
        })

    return {
        "job_id": ocr_final.get("job_id"),
        "pages": translated_pages,
        "engine": "llm_v1"
    }
