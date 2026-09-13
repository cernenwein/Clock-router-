# Feature 003: Push validation and local provider harness

- Status: Active
- Owner: Clockwork
- Created: 2026-09-13
- Updated: 2026-09-13

## Problem

Local pushes, review-branch pushes, and direct default-branch writes currently
have different validation behavior. ClockRouter also lacks a repeatable,
privacy-safe smoke test for LM Studio and Ollama.

## Outcomes

- Every pushed branch receives GitHub CI validation.
- Local pre-push failures explain the failed gate and recovery path.
- Automated changes use review branches and pull requests instead of direct
  default-branch mutation.
- An operator can validate LM Studio or Ollama and a ClockRouter chat round trip.
- Live models are never required or contacted by CI.

## Non-goals

- Weakening validation, bypassing repository safety controls, downloading
  models, benchmarking quality, cloud-provider testing, or automatic fallback.

## Requirements

- R1: One script owns local pre-push validation and returns nonzero on failure.
- R2: CI runs on every branch push and every pull request.
- R3: Push documentation distinguishes repairable validation failure from the
  intentional review-branch boundary.
- R4: The harness supports LM Studio and Ollama OpenAI-compatible base URLs.
- R5: Non-loopback access requires explicit private-network opt-in; public IP
  literals are denied.
- R6: Harness output and errors contain no prompt, response, token, or secret.
- R7: CI tests harness logic without contacting a live provider.

## Acceptance scenarios

1. A valid feature-branch push runs local tests and remote CI.
2. A stale lockfile stops locally with a documented recovery path.
3. A running local provider can list models and complete a ClockRouter request.
4. A public provider address is rejected before network access.
5. CI completes with no local model server present.

## Security, privacy, and cost

The harness uses one fixed synthetic prompt and does not print response content
or credentials. Local and explicitly trusted private-network endpoints are
eligible; public IP literals fail closed. GitHub CI never downloads model
weights or performs inference, so the change adds only ordinary CI minutes.

## Verification evidence

| Date | Command/scenario | Result |
|---|---|---|
| 2026-09-13 | `pytest tests/test_local_provider_harness.py` | Passed in PR #6 (43-test suite) |
| 2026-09-13 | Pull-request CI | Passed in PR #6, run 118 |
| 2026-09-13 | Live LM Studio round trip | Pending on LittleMac |
| 2026-09-13 | Live Ollama round trip | Pending on LittleMac |

## Change log

- 2026-09-13: Spec activated; implementation prepared on a review branch.
- 2026-09-13: Repaired push-script and Markdown escaping; CI now executes the push gate.
