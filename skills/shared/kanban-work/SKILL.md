---
name: kanban-work
description: Create, execute, review, recover, and complete durable multi-profile work on the AI Co-Founder Kanban board.
---

# Durable Kanban Work

Use Kanban for work that crosses agents, outlives the current conversation,
depends on another result, needs review, or may pause for human input.

## Contract

Before dispatch, the task must state:

- outcome and business reason;
- owner and reviewer;
- deliverable and durable artifact location;
- inputs and source links;
- dependencies;
- allowed actions and prohibited actions;
- approval boundary;
- budget or cost ceiling when relevant;
- acceptance tests;
- idempotency key for retried automation.

Workers begin by reading the active task. Use comments for progress that another
worker or human needs. Send heartbeats during long operations. Attach durable
artifacts before a scratch workspace disappears.

Complete only with a structured summary of result, evidence, artifacts,
verification, and follow-ups. Request review when required. Block with one
specific question when human input is truly necessary. Never mark a task done
because time or context is running low.

Root projects belong to AI Co-Founder. Department leaders may create child
tasks inside their scope. Reviewers and ordinary workers do not create a new
program of work without routing it upward.
