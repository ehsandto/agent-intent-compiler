# Security

## Retry-safe compilation lifecycle

The stored `reserved_version` is the finalized active version, not the highest submitted attempt. `REQUIRES_REVISION`, `UNAVAILABLE`, `ABANDONED`, and `STALE` attempts remain immutable and may be replaced at the same logical version. Replacements bind `replacement_of`, a monotonic attempt number, and the current active parent. Only the latest attempt can activate. Activation rechecks the parent/head and permanently closes the finalized version slot.

Planner consent prevents arbitrary plan attribution. Version slots are reserved at submission and cannot be overwritten. Activation verifies the parent against the live head. Validators bind source count, statuses, HTTP codes, fingerprints, hash matches, graph metrics, every semantic field, final state, and record fingerprint. No numeric tolerance or free-form explanation controls execution.
