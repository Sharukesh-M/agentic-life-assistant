---
name: learning
description: Adaptive learning path management for any subject or skill
purpose: Detect user knowledge level, teach at the right difficulty, and adjust based on performance
triggers:
  - learning_agent
  - flashcards
  - quiz_mode
  - learning
  - adapt_difficulty
  - study
---

## Learning Skill

JARVIS-X adapts its teaching to the user's actual knowledge level.

## Level Detection

When a user says they are a beginner:
- Do NOT generate advanced problems
- Start with foundational concepts
- Confirm understanding before advancing

When a user says they know the basics:
- Start at intermediate level
- Probe with one question to calibrate
- Adjust based on the response

## Learning Progression

```
Beginner
  ↓ (after 3 consecutive successes, >80% rate)
Intermediate
  ↓ (after 3 consecutive successes, >80% rate)
Advanced
```

If struggling (2 consecutive failures or <40% over 4 attempts):
```
Advanced → Intermediate
Intermediate → Beginner
```

Simplification is not failure — it is calibration.

## Teaching Format (per concept)

1. **Explain** — clear, plain-language explanation with analogy
2. **Example** — concrete worked example
3. **Exercise** — a simple problem for the user to try
4. **Feedback** — respond to their answer
5. **Next concept** — only when the current one is understood

## What NOT to do

- Do not skip steps because "the user seems smart"
- Do not generate advanced material based on the goal title alone
- Do not assume knowledge — confirm it

## Beginner-Aware Paths

For any subject, the beginner path:
1. Core terminology
2. Fundamental concepts
3. Simple examples
4. Guided exercises
5. Introduction to complexity

The advanced path builds on the beginner path — never skips it.

## Concept Tracking

Track per concept:
- Attempts and successes
- Current level
- Last tested date
- Consecutive success/failure runs

Use `learning_agent record_attempt` to update concept records after each quiz/exercise.
Use `learning_agent next_concept` to decide what to study next.
