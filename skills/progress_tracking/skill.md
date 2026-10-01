---
name: progress_tracking
description: Track task completion, detect skip patterns, and report progress without judgment
purpose: Provide honest, non-judgmental progress data that improves future planning
triggers:
  - progress_agent
  - progress_tracking
  - progress_report
  - weekly_review
  - skip_pattern
---

## Progress Tracking Skill

Progress data exists to IMPROVE planning, not to criticize behavior.

## Reporting Principles

NEVER say:
> "You failed your plan."
> "You only completed 3 out of 7 tasks."
> "You've been skipping GATE study."

ALWAYS say:
> "You completed 3 of 7 tasks this week. The remaining tasks are still pending."
> "GATE has been skipped a few times around 7 PM."

The distinction is tone — the facts are the same.

## What to Track

Per task:
- Status: pending / completed / skipped / postponed
- Completion time (when done)
- Skip count and reasons (when skipped)
- Scheduled slot (for pattern detection)

Per goal:
- Total tasks created
- Completed / skipped counts
- Completion rate
- Milestone progress

## Skip Pattern Detection

A skip pattern exists when:
- 3 or more consecutive skips of tasks for the same goal
- OR a consistent time slot (e.g., always skipped at 7 PM)

When a pattern is detected:
1. Do NOT reschedule automatically
2. Mention it naturally in the next proactive check-in OR when the user asks
3. Ask ONE question: "Want me to try a different time or smaller sessions?"
4. Apply only after user confirms

## Weekly Review Format

```
This week:
• Python: 5 of 6 sessions completed. Great consistency.
• GATE: 2 of 5 sessions completed. Sessions at 7 PM were skipped 3 times.
• IELTS: 3 of 4 completed.

Observation: GATE sessions at 7 PM have been missed a few times. 
Want me to move them to a later slot?
```

## Progress Cycle

```
TASK COMPLETED
    ↓
progress_agent.complete_task()
    ↓
TaskStore.update(status=completed)
    ↓
PlanningAgent (next task or adaptive review)
```

```
TASK SKIPPED
    ↓
progress_agent.skip_task()
    ↓
TaskStore.update(status=skipped, skip_count+1)
    ↓
After 3 skips: ProactiveAgent surfaces the pattern
```
