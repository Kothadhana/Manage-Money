"""Financial calculation, month selection, freshness check, and INR formatting.

All functions in this module are pure and independent of Streamlit so they can
be unit-tested directly with pytest and reused across future backends or APIs.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

import pandas as pd


@dataclass(frozen=True)
class FreshnessStatus:
    """Outcome of comparing the system's current month against latest data."""

    has_data: bool
    is_outdated: bool
    current_period: pd.Period
    latest_period: pd.Period | None
    message: str | None


@dataclass(frozen=True)
class MonthlySummary:
    """Aggregated income, expenses, and net savings for a single month."""

    period: pd.Period | None
    monthly_income: float
    monthly_expenses: float
    monthly_savings: float
    transaction_count: int
    has_data: bool


@dataclass(frozen=True)
class DashboardSnapshot:
    """Complete computed view-model consumed by the Money Manager dashboard."""

    selected_period: pd.Period | None
    freshness: FreshnessStatus
    monthly_summary: MonthlySummary
    monthly_comparison: pd.DataFrame
    latest_savings: pd.DataFrame
    total_savings_balance: float
    latest_debts: pd.DataFrame
    total_outstanding_debt: float


def format_inr(amount: float | int) -> str:
    """Format a numeric value as Indian Rupees with Indian number grouping.

    Examples:
        85000     -> '₹85,000'
        450000    -> '₹4,50,000'
        1250000   -> '₹12,50,000'
        -15000    -> '-₹15,000'
        1250.5    -> '₹1,250.50'
    """
    value = Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    is_negative = value < 0
    abs_value = abs(value)

    whole_part = int(abs_value)
    fractional_part = abs_value - Decimal(whole_part)

    digits = str(whole_part)
    if len(digits) <= 3:
        grouped = digits
    else:
        last_three = digits[-3:]
        remaining = digits[:-3]
        chunks: list[str] = []
        while len(remaining) > 2:
            chunks.append(remaining[-2:])
            remaining = remaining[:-2]
        if remaining:
            chunks.append(remaining)
        chunks.reverse()
        grouped = ",".join(chunks) + "," + last_three

    if fractional_part != Decimal("0.00"):
        paise = f"{fractional_part:.2f}"[1:]  # e.g. '.50'
        formatted = f"₹{grouped}{paise}"
    else:
        formatted = f"₹{grouped}"

    return f"-{formatted}" if is_negative else formatted


def format_period_label(period: pd.Period | None) -> str:
    """Format a monthly Period as 'Month YYYY' (e.g., 'October 2026')."""
    if period is None:
        return "No data"
    return period.to_timestamp().strftime("%B %Y")


def _with_period_column(transactions_df: pd.DataFrame) -> pd.DataFrame:
    """Return a shallow copy of transactions_df with a normalized monthly Period column."""
    if transactions_df.empty:
        return transactions_df.copy()

    df = transactions_df.copy()
    dates = pd.to_datetime(df["date"], errors="coerce")
    df = df.loc[dates.notna()].copy()
    if df.empty:
        return df
    df["date"] = dates.loc[dates.notna()]
    df["period"] = df["date"].dt.to_period("M")
    return df


def get_available_periods(transactions_df: pd.DataFrame) -> list[pd.Period]:
    """Return all distinct monthly periods present in transactions_df, sorted ascending."""
    df = _with_period_column(transactions_df)
    if df.empty:
        return []
    return sorted(df["period"].unique().tolist())


def get_latest_transaction_period(transactions_df: pd.DataFrame) -> pd.Period | None:
    """Automatically identify the latest month present in transactions_df."""
    periods = get_available_periods(transactions_df)
    if not periods:
        return None
    return periods[-1]


def check_data_freshness(
    latest_period: pd.Period | None,
    reference_date: date | None = None,
) -> FreshnessStatus:
    """Compare the current local month with the latest available transaction month.

    If the latest available transaction month is older than the current month,
    returns an outdated status with a clear human-readable message explaining
    which month is missing and which month's figures are shown below.
    """
    today = reference_date or date.today()
    current_period = pd.Period(year=today.year, month=today.month, freq="M")

    if latest_period is None:
        return FreshnessStatus(
            has_data=False,
            is_outdated=False,
            current_period=current_period,
            latest_period=None,
            message=(
                "No transaction data is available. Add income or expense records to "
                "data/transactions.csv to view monthly figures."
            ),
        )

    if latest_period < current_period:
        current_label = format_period_label(current_period)
        latest_label = format_period_label(latest_period)
        latest_month_name = latest_period.to_timestamp().strftime("%B")
        return FreshnessStatus(
            has_data=True,
            is_outdated=True,
            current_period=current_period,
            latest_period=latest_period,
            message=(
                f"Data may be outdated. No transaction data is available for {current_label}. "
                f"The latest available data is for {latest_label}. "
                f"Showing {latest_month_name}'s figures below."
            ),
        )

    return FreshnessStatus(
        has_data=True,
        is_outdated=False,
        current_period=current_period,
        latest_period=latest_period,
        message=None,
    )


def calculate_monthly_summary(
    transactions_df: pd.DataFrame,
    period: pd.Period | None = None,
) -> MonthlySummary:
    """Calculate Monthly Income, Monthly Expenses, and Monthly Savings for a period.

    When `period` is omitted, automatically selects the latest available month
    in `transactions_df` rather than defaulting to zero for a missing current month.
    """
    df = _with_period_column(transactions_df)
    if df.empty:
        return MonthlySummary(
            period=None,
            monthly_income=0.0,
            monthly_expenses=0.0,
            monthly_savings=0.0,
            transaction_count=0,
            has_data=False,
        )

    target_period = period if period is not None else df["period"].max()
    month_df = df.loc[df["period"] == target_period]

    if month_df.empty:
        return MonthlySummary(
            period=target_period,
            monthly_income=0.0,
            monthly_expenses=0.0,
            monthly_savings=0.0,
            transaction_count=0,
            has_data=False,
        )

    types = month_df["type"].astype(str).str.strip().str.lower()
    amounts = pd.to_numeric(month_df["amount"], errors="coerce").fillna(0.0)

    monthly_income = float(amounts.loc[types == "income"].sum())
    monthly_expenses = float(amounts.loc[types == "expense"].sum())
    monthly_savings = monthly_income - monthly_expenses

    return MonthlySummary(
        period=target_period,
        monthly_income=monthly_income,
        monthly_expenses=monthly_expenses,
        monthly_savings=monthly_savings,
        transaction_count=int(len(month_df)),
        has_data=True,
    )


def calculate_monthly_comparison(transactions_df: pd.DataFrame) -> pd.DataFrame:
    """Build a chronological month-by-month Income vs. Expenses comparison table."""
    columns = ["period", "month_label", "month_full_label", "income", "expenses", "savings"]
    df = _with_period_column(transactions_df)
    if df.empty:
        return pd.DataFrame(columns=columns)

    df["type"] = df["type"].astype(str).str.strip().str.lower()
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)

    grouped = (
        df.groupby(["period", "type"], as_index=False)["amount"]
        .sum()
        .pivot(index="period", columns="type", values="amount")
        .fillna(0.0)
        .sort_index()
    )

    if "income" not in grouped.columns:
        grouped["income"] = 0.0
    if "expense" not in grouped.columns:
        grouped["expense"] = 0.0

    result = pd.DataFrame(
        {
            "period": grouped.index,
            "month_label": [p.to_timestamp().strftime("%b %Y") for p in grouped.index],
            "month_full_label": [p.to_timestamp().strftime("%B %Y") for p in grouped.index],
            "income": grouped["income"].astype(float).values,
            "expenses": grouped["expense"].astype(float).values,
        }
    )
    result["savings"] = result["income"] - result["expenses"]
    return result.reset_index(drop=True)


def _get_latest_snapshot_per_entity(
    df: pd.DataFrame,
    entity_col: str,
    value_col: str,
) -> pd.DataFrame:
    """Select only the latest dated snapshot for each distinct entity.

    Historical snapshots are intentionally never summed together.
    """
    columns = ["date", entity_col, value_col]
    if df.empty:
        return pd.DataFrame(columns=columns)

    working = df.copy()
    working["date"] = pd.to_datetime(working["date"], errors="coerce")
    working[value_col] = pd.to_numeric(working[value_col], errors="coerce")
    working[entity_col] = working[entity_col].astype(str).str.strip()
    working = working.dropna(subset=["date", value_col])
    working = working.loc[working[entity_col] != ""]

    if working.empty:
        return pd.DataFrame(columns=columns)

    # Preserve file order for ties on the exact same date via stable mergesort
    working = working.sort_values(by="date", kind="mergesort")
    latest = working.drop_duplicates(subset=[entity_col], keep="last")
    latest = latest.sort_values(by=[value_col, entity_col], ascending=[False, True])
    return latest[columns].reset_index(drop=True)


def get_latest_savings_balances(savings_df: pd.DataFrame) -> pd.DataFrame:
    """Return the latest dated balance snapshot for each savings account."""
    return _get_latest_snapshot_per_entity(savings_df, "account", "balance")


def calculate_total_savings_balance(savings_df: pd.DataFrame) -> float:
    """Calculate total current savings balance across all accounts using latest snapshots."""
    latest = get_latest_savings_balances(savings_df)
    if latest.empty:
        return 0.0
    return float(latest["balance"].sum())


def get_latest_debt_balances(debts_df: pd.DataFrame) -> pd.DataFrame:
    """Return the latest dated outstanding balance snapshot for each loan."""
    return _get_latest_snapshot_per_entity(debts_df, "loan", "outstanding_balance")


def calculate_total_outstanding_debt(debts_df: pd.DataFrame) -> float:
    """Calculate total outstanding debt across all loans using latest snapshots."""
    latest = get_latest_debt_balances(debts_df)
    if latest.empty:
        return 0.0
    return float(latest["outstanding_balance"].sum())


def build_dashboard_snapshot(
    transactions_df: pd.DataFrame,
    savings_df: pd.DataFrame,
    debts_df: pd.DataFrame,
    reference_date: date | None = None,
) -> DashboardSnapshot:
    """Compute the complete Version 1 dashboard state from validated DataFrames."""
    latest_period = get_latest_transaction_period(transactions_df)
    freshness = check_data_freshness(latest_period, reference_date=reference_date)
    monthly_summary = calculate_monthly_summary(transactions_df, period=latest_period)
    monthly_comparison = calculate_monthly_comparison(transactions_df)

    latest_savings = get_latest_savings_balances(savings_df)
    total_savings = float(latest_savings["balance"].sum()) if not latest_savings.empty else 0.0

    latest_debts = get_latest_debt_balances(debts_df)
    total_debt = (
        float(latest_debts["outstanding_balance"].sum()) if not latest_debts.empty else 0.0
    )

    return DashboardSnapshot(
        selected_period=latest_period,
        freshness=freshness,
        monthly_summary=monthly_summary,
        monthly_comparison=monthly_comparison,
        latest_savings=latest_savings,
        total_savings_balance=total_savings,
        latest_debts=latest_debts,
        total_outstanding_debt=total_debt,
    )
