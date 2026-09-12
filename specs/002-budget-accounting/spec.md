# Feature 002: Budget accounting

- Status: Active
- Owner: Clockwork
- Created: 2026-09-12
- Updated: 2026-09-12

## Problem

ClockRouter can technically route to a cloud URL, but it has no atomic record of
committed spend. A concurrent agent workload could therefore exceed a nominal
limit before any completed response is recorded.

## Outcomes

- Cloud work is denied before dispatch when its conservative estimate exceeds a limit.
- Per-request, UTC-day, and UTC-month limits are enforced atomically in SQLite.
- Concurrent reservations cannot collectively pass a budget.
- Unknown prices or estimates fail closed.
- Local routes never consume a cloud budget.

## Non-goals

- Provider-specific billing reconciliation, currency conversion, dashboards,
  prompt logging, cloud adapters, or tokenization exactness.

## Requirements

- R1: Cloud models declare non-negative input and output prices per million tokens.
- R2: Request estimates round up and include both prompt and maximum output cost.
- R3: Missing prices or token estimates deny cloud dispatch.
- R4: One SQLite transaction checks all limits and records a reservation.
- R5: Limits exist for one request, one UTC day, and one UTC calendar month.
- R6: A request ID is idempotent and cannot reserve twice.
- R7: Finalization replaces the reservation with actual cost when trustworthy usage exists.
- R8: Stored records contain metadata and costs only, never prompt or completion content.

## Acceptance scenarios

1. A reservation below every limit commits and appears in the current windows.
2. A request above any limit is rejected and no row is charged.
3. Concurrent reservations near a limit permit only the affordable subset.
4. Reusing a request ID does not reserve funds twice.
5. Local work bypasses budget reservation.

## Security, privacy, and cost

SQLite contains request IDs, project/model identifiers, timestamps, status, and
costs. It never contains request bodies, responses, credentials, or raw errors.
Conservative reservations may temporarily overstate cost; that is safer than an
overspend and can be reconciled after trustworthy provider usage arrives.

## Verification evidence

| Date | Command/scenario | Result |
|---|---|---|
| 2026-09-12 | `uv run pytest tests/test_accounting.py` | 6 passed |
| 2026-09-12 | `uv run pytest -n auto` | 30 passed across 9 workers |

## Change log

- 2026-09-12: Spec activated before adding any cloud adapter.
- 2026-09-12: Atomic reservation ledger and concurrency coverage added.
