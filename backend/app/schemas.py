from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict

class OCRBlock(BaseModel):
    block_id: str
    original_text: str
    bbox: List[int]  # [x1,y1,x2,y2]
    is_speech: bool = True
    is_sfx: bool = False
    shape_hint: str = "unknown"
    max_characters: int = 40
    max_lines: int = 2
    notes: str = ""
    group_id: Optional[str] = None
    reading_order: Optional[int] = None
    block_type: str = "unknown"

class OCRPage(BaseModel):
    page_number: int
    image_file: str
    blocks: List[OCRBlock]

class OCRDocument(BaseModel):
    chapter_id: str = "001"
    pages: List[OCRPage]

class JobCreated(BaseModel):
    job_id: str
    status: str = "created"

class UploadResult(BaseModel):
    job_id: str
    page_number: int
    saved_as: str

class PipelineRunResult(BaseModel):
    status: str
    checkpoint_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None

class CheckpointInfo(BaseModel):
    checkpoint_id: str
    job_id: str
    page_number: int
    label: str
    status: str
    created_on: str
    approved_on: Optional[str] = None
    context_keys: List[str] = Field(default_factory=list)

class JobSummary(BaseModel):
    job_id: str
    status: str
    created_on: Optional[str] = None
    page_count: int = 0
    pages: List[Dict[str, Any]] = []
