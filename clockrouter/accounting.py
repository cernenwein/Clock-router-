import math
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path


class BudgetExceeded(ValueError):
    pass


@dataclass(frozen=True)
class BudgetLimits:
    request_microusd: int
    daily_microusd: int
    monthly_microusd: int


def estimate_cost_microusd(
    input_tokens: int,
    output_tokens: int,
    input_usd_per_million: Decimal,
    output_usd_per_million: Decimal,
) -> int:
    if input_tokens < 0 or output_tokens < 0:
        raise ValueError("token estimates must be non-negative")
    if input_usd_per_million < 0 or output_usd_per_million < 0:
        raise ValueError("prices must be non-negative")
    cost = input_tokens * input_usd_per_million + output_tokens * output_usd_per_million
    return math.ceil(cost)


class BudgetLedger:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        connection.execute("PRAGMA busy_timeout = 10000")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS reservations (
                    request_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    project TEXT NOT NULL,
                    model TEXT NOT NULL,
                    charged_microusd INTEGER NOT NULL CHECK (charged_microusd >= 0),
                    status TEXT NOT NULL
                )
                """
            )

    def reserve(
        self,
        request_id: str,
        project: str,
        model: str,
        estimate_microusd: int,
        limits: BudgetLimits,
        *,
        now: datetime | None = None,
    ) -> None:
        if estimate_microusd < 0:
            raise ValueError("cost estimate must be non-negative")
        instant = (now or datetime.now(UTC)).astimezone(UTC)
        day_start = instant.replace(hour=0, minute=0, second=0, microsecond=0)
        month_start = day_start.replace(day=1)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            if connection.execute(
                "SELECT 1 FROM reservations WHERE request_id = ?", (request_id,)
            ).fetchone():
                connection.commit()
                return
            daily = self._sum_since(connection, day_start)
            monthly = self._sum_since(connection, month_start)
            checks = (
                ("request", estimate_microusd, limits.request_microusd),
                ("daily", daily + estimate_microusd, limits.daily_microusd),
                ("monthly", monthly + estimate_microusd, limits.monthly_microusd),
            )
            for name, attempted, maximum in checks:
                if attempted > maximum:
                    connection.rollback()
                    raise BudgetExceeded(f"{name} cloud budget exceeded")
            connection.execute(
                "INSERT INTO reservations VALUES (?, ?, ?, ?, ?, ?)",
                (request_id, instant.isoformat(), project, model, estimate_microusd, "reserved"),
            )
            connection.commit()

    @staticmethod
    def _sum_since(connection: sqlite3.Connection, start: datetime) -> int:
        row = connection.execute(
            "SELECT COALESCE(SUM(charged_microusd), 0) FROM reservations WHERE created_at >= ?",
            (start.isoformat(),),
        ).fetchone()
        return int(row[0])

    def total_microusd(self) -> int:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT COALESCE(SUM(charged_microusd), 0) FROM reservations"
            ).fetchone()
        return int(row[0])

    def finalize(self, request_id: str, actual_microusd: int) -> None:
        if actual_microusd < 0:
            raise ValueError("actual cost must be non-negative")
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE reservations
                SET charged_microusd = ?, status = 'completed'
                WHERE request_id = ?
                """,
                (actual_microusd, request_id),
            )
            if cursor.rowcount != 1:
                raise KeyError("unknown budget reservation")


def usd_to_microusd(value: Decimal) -> int:
    return math.ceil(value * Decimal(1000000))
