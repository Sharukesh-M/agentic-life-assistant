"""
core/skill_loader.py - JARVIS-X Skill Registry & Loader

Phase 2 addition: Discovers and loads skill definition files from the
skills/ directory. Each skill is a Markdown file (skill.md) with a YAML
frontmatter block describing its name, purpose, triggers, and capabilities.

Skill files provide operational guidance that is loaded contextually into
the LLM system prompt when that skill is relevant to the current request.
They are NOT loaded into every call -- only when the Orchestrator selects
them for a specific agent dispatch.

No existing code is modified.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("jarvis.skill_loader")

# ---------------------------------------------------------------------------
# YAML frontmatter parser (no external deps -- keeps the dep tree clean)
# ---------------------------------------------------------------------------

def _parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Parse YAML-style frontmatter from a Markdown string.

    Returns (metadata_dict, body_text). The body is the Markdown content
    below the closing ---.

    Supports:
      - simple key: value
      - inline list: key: [a, b, c]
      - block list:
          key:
            - item1
            - item2
    Intentionally minimal -- skills should not need complex YAML.
    """
    meta: dict[str, Any] = {}
    body = text

    # Match optional frontmatter block: ---\n...\n---
    fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)", text, re.DOTALL)
    if not fm_match:
        return meta, body

    fm_text = fm_match.group(1)
    body = fm_match.group(2)

    lines = fm_text.splitlines()
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()

        # Skip blank lines, comments, stray block-list items (handled in key loop)
        if not stripped or stripped.startswith("#") or stripped.startswith("- "):
            i += 1
            continue

        if ":" not in stripped:
            i += 1
            continue

        key, _, raw_val = stripped.partition(":")
        key = key.strip()
        raw_val = raw_val.strip()

        # Inline list: [a, b, c]
        if raw_val.startswith("[") and raw_val.endswith("]"):
            items = [it.strip().strip('"').strip("'") for it in raw_val[1:-1].split(",")]
            meta[key] = [it for it in items if it]
            i += 1
            continue

        # Empty value after colon -> look ahead for block list items (YAML block sequence)
        if raw_val == "":
            block_items = []
            j = i + 1
            while j < len(lines):
                next_stripped = lines[j].strip()
                if next_stripped.startswith("- "):
                    block_items.append(next_stripped[2:].strip().strip('"').strip("'"))
                    j += 1
                elif not next_stripped:
                    j += 1
                    break
                else:
                    break
            if block_items:
                meta[key] = block_items
                i = j
                continue

        # Simple scalar value
        meta[key] = raw_val.strip('"').strip("'")
        i += 1

    return meta, body



# ---------------------------------------------------------------------------
# SkillRecord
# ---------------------------------------------------------------------------

@dataclass
class SkillRecord:
    """One discovered and parsed skill.

    Attributes:
        name         -- Unique identifier from frontmatter
        description  -- Short description from frontmatter
        purpose      -- Longer purpose statement from frontmatter
        triggers     -- List of keywords/tool names that activate this skill
        dependencies -- Other skill names this skill depends on
        instructions -- The full Markdown body (operational guidance for LLM)
        file         -- Path to the skill.md file on disk
        valid        -- False if parsing failed
        error        -- Error message if invalid
    """
    name: str
    description: str = ""
    purpose: str = ""
    triggers: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    instructions: str = ""
    file: str = ""
    valid: bool = True
    error: str = ""

    def as_context_block(self) -> str:
        """Format the skill as a context block for injection into a system prompt."""
        lines = [
            f"[SKILL: {self.name.upper()}]",
            f"Purpose: {self.purpose or self.description}",
            "",
            self.instructions.strip(),
            f"[/SKILL: {self.name.upper()}]",
        ]
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# SkillRegistry
# ---------------------------------------------------------------------------

class SkillRegistry:
    """Stores all discovered skills and provides lookup by name or trigger.

    Usage:
        registry = discover_skills(skills_dir=Path("skills/"))
        skill = registry.get("goal_management")
        skill = registry.find_by_trigger("goal_tracker")
        context = registry.context_for(["goal_management", "task_planning"])
    """

    def __init__(
        self,
        skills: dict[str, SkillRecord],
        logger_fn: Optional[callable] = None,
    ) -> None:
        self._skills = skills
        self._log = logger_fn or (lambda m: logger.info(m))

    def get(self, name: str) -> Optional[SkillRecord]:
        return self._skills.get(name)

    def has(self, name: str) -> bool:
        return name in self._skills

    def list(self, valid_only: bool = True) -> list[SkillRecord]:
        records = list(self._skills.values())
        if valid_only:
            records = [r for r in records if r.valid]
        return records

    def names(self) -> list[str]:
        return list(self._skills.keys())

    def find_by_trigger(self, trigger: str) -> Optional[SkillRecord]:
        """Find the first valid skill whose triggers list contains this keyword."""
        trigger_lower = trigger.lower().strip()
        for record in self._skills.values():
            if not record.valid:
                continue
            if any(t.lower() == trigger_lower for t in record.triggers):
                return record
            # Partial match
            if any(trigger_lower in t.lower() for t in record.triggers):
                return record
        return None

    def find_all_for_triggers(self, triggers: list[str]) -> list[SkillRecord]:
        """Return all skills that match any of the given triggers (no duplicates)."""
        seen: set[str] = set()
        results: list[SkillRecord] = []
        for trigger in triggers:
            skill = self.find_by_trigger(trigger)
            if skill and skill.name not in seen:
                seen.add(skill.name)
                results.append(skill)
        return results

    def context_for(self, skill_names: list[str]) -> str:
        """Concatenate context blocks for a set of skill names.

        Returns an empty string if no named skills exist.
        Used by the Orchestrator to build skill context for a specific agent call.
        """
        blocks = []
        for name in skill_names:
            record = self._skills.get(name)
            if record and record.valid:
                blocks.append(record.as_context_block())
        return "\n\n".join(blocks)


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

def discover_skills(
    skills_dir: Path,
    logger_fn: Optional[callable] = None,
) -> SkillRegistry:
    """Scan skills_dir recursively for skill.md files and build a SkillRegistry.

    Each skill lives in its own subdirectory:
        skills/goal_management/skill.md
        skills/learning/skill.md
        ...

    Invalid files are skipped with a warning. Discovery never raises.
    """
    log = logger_fn or (lambda m: logger.info(m))
    records: dict[str, SkillRecord] = {}

    if not skills_dir.exists():
        log(f"[SkillLoader] skills_dir does not exist: {skills_dir}")
        return SkillRegistry(records, log)

    skill_files = list(skills_dir.rglob("skill.md"))
    log(f"[SkillLoader] Found {len(skill_files)} skill file(s) in {skills_dir}")

    for skill_file in sorted(skill_files):
        try:
            text = skill_file.read_text(encoding="utf-8")
            meta, body = _parse_frontmatter(text)

            name = str(meta.get("name", "")).strip()
            if not name:
                # Derive name from directory if not in frontmatter
                name = skill_file.parent.name

            if not name:
                log(f"[SkillLoader] SKIP {skill_file}: no name")
                continue

            triggers = meta.get("triggers", [])
            if isinstance(triggers, str):
                triggers = [t.strip() for t in triggers.split(",") if t.strip()]

            dependencies = meta.get("dependencies", [])
            if isinstance(dependencies, str):
                dependencies = [d.strip() for d in dependencies.split(",") if d.strip()]

            record = SkillRecord(
                name=name,
                description=str(meta.get("description", "")).strip(),
                purpose=str(meta.get("purpose", "")).strip(),
                triggers=triggers,
                dependencies=dependencies,
                instructions=body.strip(),
                file=str(skill_file),
                valid=True,
            )

            if name in records:
                log(f"[SkillLoader] WARNING: Duplicate skill '{name}' in {skill_file} -- skipping")
                continue

            records[name] = record
            log(f"[SkillLoader] Loaded skill: {name} ({len(record.triggers)} triggers)")

        except Exception as exc:
            log(f"[SkillLoader] ERROR loading {skill_file}: {exc}")
            # Store an invalid placeholder so the error is visible in list()
            err_name = skill_file.parent.name or str(skill_file)
            if err_name not in records:
                records[err_name] = SkillRecord(
                    name=err_name, valid=False, error=str(exc), file=str(skill_file)
                )

    return SkillRegistry(records, log)


# ---------------------------------------------------------------------------
# Process-level singleton
# ---------------------------------------------------------------------------

_default_registry: Optional[SkillRegistry] = None
_registry_lock = __import__("threading").Lock()


def get_skill_registry(skills_dir: Optional[Path] = None) -> SkillRegistry:
    """Return the process-level SkillRegistry singleton.

    On first call, discovers skills from skills_dir (defaults to
    <project_root>/skills/ relative to this file).
    """
    global _default_registry
    if _default_registry is None:
        with _registry_lock:
            if _default_registry is None:
                if skills_dir is None:
                    skills_dir = Path(__file__).resolve().parent.parent / "skills"
                _default_registry = discover_skills(
                    skills_dir=skills_dir,
                    logger_fn=lambda m: print(m),
                )
    return _default_registry


def reset_skill_registry() -> None:
    """Reset the singleton (for tests only)."""
    global _default_registry
    with _registry_lock:
        _default_registry = None
