"""The two system prompts, read from /prompts at every call.

Reading on each call (a few KB) means a prompt edited on the VM applies on
the next generation or grading, without a rebuild nor a restart
(PROMPT_TUNING.md). The prompt text is the cached prefix: it only changes
when you edit it.
"""

from __future__ import annotations

import os
from pathlib import Path

_REPO_PROMPTS = Path(__file__).resolve().parents[3] / "prompts"


def prompts_dir() -> Path:
    configured = os.getenv("PROMPTS_DIR")
    if configured and Path(configured, "generate.md").exists():
        return Path(configured)
    return _REPO_PROMPTS


def load(name: str) -> str:
    """`generate` or `grade`: the markdown file, stripped."""
    path = prompts_dir() / f"{name}.md"
    if not path.exists():
        raise RuntimeError(f"Prompt introuvable : {path}. Le dossier prompts/ est-il monté ?")
    return path.read_text(encoding="utf-8").strip()
