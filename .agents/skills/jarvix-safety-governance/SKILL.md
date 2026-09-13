---
name: jarvix-safety-governance
description: Guidelines for safety overlays, confirmation gates, the Reversibility Test, and error recovery policies. Use when implementing or auditing agent authorization, safety checks, or error handling.
---

# JARVIX Safety & Governance Guide

This skill governs safety enforcement, the Reversibility Test, confirmation prompts, and error recovery policies across all JARVIX agents.

## 1. Reversibility Test

Before executing any tool or action:

- **Low-Impact / Easily Reversible** (e.g. creating draft text, local task object): Proceed without explicit confirmation.
- **High-Impact / Hard to Reverse / Externally Visible** (e.g. creating Google Calendar event, invoking external API, initiating external compute job): Require explicit user confirmation first.

## 2. Confirmation Format

When confirmation is required, state the action plainly and ask a direct binary question:
> *"This will create an event on your Google Calendar for Wednesday 3:00 PM – 4:00 PM titled 'Model Training Session'. Should I proceed? (Yes/No)"*

## 3. Strict Prohibitions

- Never expose secrets, tokens, or API keys in response output.
- Never treat previous turn context or emotional tone as authorization to bypass confirmation.
- Never report indirect signals (e.g. git commit) as task completion without explicit user confirmation or verified completion signal.

## 4. Transparent Error Recovery

When a tool or service call fails:
1. Do not swallow errors or pretend the action succeeded.
2. Report failure plainly in user-friendly language (no stack trace dumps to user).
3. Offer concrete next steps: retry, re-authenticate, or proceed with explicit gap awareness.
