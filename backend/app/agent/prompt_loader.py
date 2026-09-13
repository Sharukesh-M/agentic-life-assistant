"""
Dynamic Prompt Assembly Service for JARVIX Agents.
Combines Core System Prompt + Standing Overlays + Specialist Prompt + Context.
"""

import os
from typing import Optional, List

PROMPTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "prompts"))

def load_prompt_file(relative_path: str) -> str:
    full_path = os.path.join(PROMPTS_DIR, relative_path)
    if not os.path.exists(full_path):
        raise FileNotFoundError(f"Prompt file not found at: {full_path}")
    with open(full_path, "r", encoding="utf-8") as f:
        return f.read().strip()

def assemble_agent_prompt(
    specialist_prompt_path: Optional[str] = None,
    include_hallucination_overlay: bool = True,
    include_safety_overlay: bool = True,
    include_error_overlay: bool = True,
    custom_instructions: Optional[str] = None
) -> str:
    """
    Assembles a modular system prompt dynamically.
    Structure: Core System Prompt + Standing Overlays + Specialist Prompt + Custom Instructions.
    """
    sections: List[str] = []

    # 1. Core System Prompt
    core_system = load_prompt_file("core/system.md")
    sections.append(core_system)

    # 2. Standing Overlays
    sections.append("=== STANDING OVERLAYS ===")
    if include_hallucination_overlay:
        sections.append(load_prompt_file("overlays/hallucination_prevention.md"))
    if include_safety_overlay:
        sections.append(load_prompt_file("overlays/safety_confirmation.md"))
    if include_error_overlay:
        sections.append(load_prompt_file("overlays/error_recovery.md"))

    # 3. Specialist Prompt
    if specialist_prompt_path:
        sections.append("=== SPECIALIST AGENT INSTRUCTIONS ===")
        sections.append(load_prompt_file(specialist_prompt_path))

    # 4. Custom Turn Instructions
    if custom_instructions:
        sections.append("=== CURRENT TURN CONSTRAINTS ===")
        sections.append(custom_instructions.strip())

    return "\n\n".join(sections)
