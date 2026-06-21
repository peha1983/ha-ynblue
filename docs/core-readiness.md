# Home Assistant Core Readiness Notes

This document is not a promise that the integration is ready for Home Assistant Core today. It is a gap analysis for a future discussion.

## What is already aligned

- config flow based setup
- translations
- diagnostics support
- automated tests
- CI validation with hassfest and HACS checks
- local brand assets
- release-based distribution
- explicit stale-data handling and online-state exposure

## What would still need to be proven or improved

### Upstream API stability

Core inclusion is much easier when the upstream API is documented, stable, and acceptable from a maintenance perspective.

Questions to answer:

- Is the YnBlue cloud API stable enough for long-term maintenance?
- Is there a documented vendor-supported integration path or only reverse-engineered behavior?
- Are command semantics predictable across controller variants?

### Long-term maintenance commitment

Core integrations need maintainers who can keep pace with Home Assistant architectural standards and upstream breakage.

Questions to answer:

- Who owns long-term maintenance?
- Is there enough real-world user demand to justify Core review and follow-up maintenance?

### Quality scale expectations

The integration would need to be evaluated against current Home Assistant Integration Quality Scale expectations at the time of submission.

Likely focus areas:

- broader test depth
- stronger runtime observability
- consistent reauthentication and repair flows
- strict entity and device metadata quality
- stable upgrade behavior

### Product surface discipline

Any action exposed in Core should be conservative and clearly safe.

Areas to review carefully:

- chemical injection actions
- controller restart actions
- behavior when a follow-up snapshot cannot confirm the physical state

## Recommended path before any Core discussion

1. Let the HACS integration mature in public use first.
2. Collect real installation feedback and bug reports.
3. Stabilize the supported command surface across hardware variants.
4. Tighten tests around reconnection, stale data, and command confirmation.
5. Reassess demand and maintenance commitment before investing in a Core proposal.
