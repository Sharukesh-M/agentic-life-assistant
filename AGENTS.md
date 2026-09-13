# JARVIX Project Agent Guidelines

Welcome to **JARVIX – Goal-Aware Proactive Agentic AI Life Assistant**.

## Core Operational Directives for AI Coding Assistants

1. **Project Scope**: This is the JARVIX agentic AI life assistant application codebase.
2. **Primary Specification**: [docs/JARVIX_Prompt_Engineering_Specification.md](file:///Users/sharukeshm/Desktop/1/docs/JARVIX_Prompt_Engineering_Specification.md) is the primary specification for system prompts, agent architecture, memory classification, planning JSON schemas, and safety overlays.
3. **Design System**: [DESIGN.md](file:///Users/sharukeshm/Desktop/1/DESIGN.md) controls visual language, UI components, accessibility standards, and token architectures.
4. **Agent Skills**: [.agents/skills/](file:///Users/sharukeshm/Desktop/1/.agents/skills) contains modular task-specific skills (AntiSlop, UX/UI, accessibility auditing, design system migration). Load skills only as needed for specific tasks.
5. **Reference Repositories**: Subdirectories under [references/](file:///Users/sharukeshm/Desktop/1/references) (`anti-slop`, `awesome-design-md`, `ux-ui-agent-skills`, `your-project`) are read-only supporting resources, NOT application source code.
6. **Codebase Inspection**: Always inspect existing implementation files before proposing or making architectural changes.
7. **No Functional Duplication**: Extend existing modules (`backend/app/`, `frontend/`) rather than creating competing components or duplicate files.
8. **Dependency Discipline**: Do not introduce unapproved third-party dependencies or pin arbitrary package versions.
9. **Preserve Working Code**: Retain existing working functionality, tests, and API signatures.
10. **Runtime Verification**: Verify changes with test scripts or build commands before declaring task completion.
