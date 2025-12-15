from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional


def _project_root() -> Path:
    # backend/app/core/checkpoints_store.py -> .../MojiTranslateAI
    p = Path(__file__).resolve()
    for parent in p.parents:
        if (parent / "data").exists() and (parent / "backend").exists():
            return parent
    # fallback: assume structure MojiTranslateAI/backend/app/core/...
    return p.parents[4]


def data_dir() -> Path:
    return Path(_project_root() / "data")


def job_dir(job_id: str) -> Path:
    return data_dir() / "jobs" / job_id


def checkpoints_dir(job_id: str) -> Path:
    return job_dir(job_id) / "checkpoints"


def checkpoint_path(job_id: str, checkpoint_id: str) -> Path:
    return checkpoints_dir(job_id) / f"{checkpoint_id}.json"


def save_checkpoint(job_id: str, checkpoint: Dict[str, Any]) -> None:
    d = checkpoints_dir(job_id)
    d.mkdir(parents=True, exist_ok=True)
    cid = checkpoint.get("checkpoint_id")
    if not cid:
        raise ValueError("checkpoint.checkpoint_id ausente")
    p = checkpoint_path(job_id, cid)
    p.write_text(json.dumps(checkpoint, ensure_ascii=False, indent=2), encoding="utf-8")


def load_checkpoint(job_id: str, checkpoint_id: str) -> Optional[Dict[str, Any]]:
    p = checkpoint_path(job_id, checkpoint_id)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def update_checkpoint(job_id: str, checkpoint_id: str, patch: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    current = load_checkpoint(job_id, checkpoint_id)
    if current is None:
        return None
    current.update(patch)
    save_checkpoint(job_id, current)
    return current
