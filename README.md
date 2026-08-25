# AgentIntentCompiler

A reusable GenLayer compilation gate between human intent and autonomous execution. An owner binds a goal, constraints, forbidden actions, an immutable intent document, and an independent planner. The planner must authenticate and accept assignment before reserving an immutable plan version.

Validators independently fetch the intent and plan documents, verify both hashes, deterministically validate the execution DAG, and independently reconstruct a bounded semantic vector covering goal completeness, constraint preservation, forbidden actions, hidden assumptions, rollback readiness, and risk. The entire report must match exactly.

Only a `COMPILED` plan at the current activation head opens `verify_execution_ready`. Unavailable sources and revision failures are stored and cannot preserve a stale positive gate.

Run `genvm-lint check contracts/AgentIntentCompiler.py` and `npm test`.
