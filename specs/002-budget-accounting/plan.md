# Implementation plan: Budget accounting

## Constitution check

- Local-first behavior: local requests bypass cloud accounting.
- Privacy enforcement: no prompt or response content enters SQLite.
- Budget enforcement: reservation happens atomically before dispatch.
- API compatibility: denied requests use the existing OpenAI-shaped error envelope.
- Explainability: denials identify the limit category without exposing sensitive data.

## Design

Use integer microdollars internally to avoid floating-point drift. A conservative
estimator rounds token charges upward. `BudgetLedger.reserve` opens an immediate
SQLite transaction, calculates UTC-window spend, checks every limit, and inserts
one idempotent reservation before releasing the write lock.

## Files and interfaces

| Path/interface | Change |
|---|---|
| `clockrouter/accounting.py` | Estimator, SQLite ledger, budget exceptions |
| `clockrouter/config.py` | Typed prices, limits, and database location |
| `clockrouter/main.py` | Reserve before cloud dispatch; reconcile completed usage |
| `tests/test_accounting.py` | Precision, limits, idempotency, concurrency |

## Configuration and migration

The ledger creates its version-one schema idempotently. Cloud models without
prices are invalid. Existing local-only configuration remains valid and incurs
no database charge.

## Test strategy

Unit tests cover rounding and each limit. Threaded tests use independent SQLite
connections against one temporary database to prove serialized reservations.
API tests will verify cloud denial occurs before the mocked upstream is called.

## Risks and rollback

SQLite lock contention is bounded by its busy timeout. Estimation error is biased
toward over-reservation. Rollback may remove enforcement code, but cloud routing
must remain disabled while budget enforcement is absent.
