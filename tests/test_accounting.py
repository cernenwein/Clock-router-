from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from pathlib import Path

import pytest

from clockrouter.accounting import (
    BudgetExceeded,
    BudgetLedger,
    BudgetLimits,
    estimate_cost_microusd,
)


def test_estimate_rounds_up_fractional_microusd() -> None:
    assert estimate_cost_microusd(1, 1, Decimal("0.10"), Decimal("0.20")) == 1


@pytest.mark.parametrize(
    ("limits", "expected_limit"),
    [
        (
            BudgetLimits(request_microusd=99, daily_microusd=1_000, monthly_microusd=1_000),
            "request",
        ),
        (BudgetLimits(request_microusd=1_000, daily_microusd=99, monthly_microusd=1_000), "daily"),
        (
            BudgetLimits(request_microusd=1_000, daily_microusd=1_000, monthly_microusd=99),
            "monthly",
        ),
    ],
)
def test_each_budget_limit_fails_closed(
    tmp_path: Path, limits: BudgetLimits, expected_limit: str
) -> None:
    ledger = BudgetLedger(tmp_path / "usage.db")

    with pytest.raises(BudgetExceeded, match=expected_limit):
        ledger.reserve("request-1", "public", "cloud", 100, limits)

    assert ledger.total_microusd() == 0


def test_request_id_is_idempotent(tmp_path: Path) -> None:
    ledger = BudgetLedger(tmp_path / "usage.db")
    limits = BudgetLimits(1_000, 1_000, 1_000)

    ledger.reserve("same-id", "public", "cloud", 100, limits)
    ledger.reserve("same-id", "public", "cloud", 100, limits)

    assert ledger.total_microusd() == 100


def test_finalize_replaces_conservative_reservation(tmp_path: Path) -> None:
    ledger = BudgetLedger(tmp_path / "usage.db")
    limits = BudgetLimits(1_000, 1_000, 1_000)
    ledger.reserve("request-1", "public", "cloud", 100, limits)

    ledger.finalize("request-1", 40)

    assert ledger.total_microusd() == 40


def test_concurrent_reservations_cannot_overspend(tmp_path: Path) -> None:
    database = tmp_path / "usage.db"
    limits = BudgetLimits(100, 500, 500)

    def reserve(index: int) -> bool:
        try:
            BudgetLedger(database).reserve(f"request-{index}", "public", "cloud", 100, limits)
        except BudgetExceeded:
            return False
        return True

    with ThreadPoolExecutor(max_workers=16) as pool:
        accepted = list(pool.map(reserve, range(20)))

    assert sum(accepted) == 5
    assert BudgetLedger(database).total_microusd() == 500
