# Implementation plan: Push validation and local provider harness

## Constitution check

- Local-first behavior: only local or explicitly trusted private endpoints are eligible.
- Privacy enforcement: fixed synthetic prompt; no content or secrets in output.
- Budget enforcement: local routes bypass cloud accounting.
- API compatibility: probe `/v1/models` and `/v1/chat/completions`.
- Explainability: report provider, selected model, route, request ID, and status.

## Design

Keep the runtime unchanged. A standalone standard-library harness checks the
provider model list and calls the running ClockRouter gateway. A small push
script owns lock and test gates. GitHub Actions runs for all pushed branches,
giving review branches an independent result before a pull request is opened.

## Files and interfaces

| Path/interface | Change |
|---|---|
| `scripts/check-push.sh` | Deterministic, diagnosable pre-push gate |
| `scripts/local_provider_harness.py` | Local provider and gateway smoke test |
| `tests/test_local_provider_harness.py` | Offline harness logic coverage |
| `.pre-commit-config.yaml` | Delegate pre-push validation to the script |
| `.github/workflows/ci.yml` | Validate every pushed branch and pull request |
| `docs/LOCAL_PROVIDER_HARNESS.md` | LM Studio/Ollama operator workflow |
| workflow documents | Explain branch-first automated changes |

## Configuration and migration

No production configuration or database migration is required. Operators set
the exact provider model ID in the existing `config/models.yaml`.

## Test strategy

Unit-test URL eligibility and model selection. Existing API tests cover the
gateway proxy. PR CI runs Ruff, the full parallel suite, Compose validation, and
the hardened container test. Live provider checks remain manual acceptance
evidence on LittleMac.

## Risks and rollback

All-branch CI consumes more Actions minutes; concurrency cancellation limits
waste. The harness could accidentally target a remote host, mitigated by
loopback defaults and explicit private-network opt-in. Revert the feature
commit to restore previous hooks and triggers.
