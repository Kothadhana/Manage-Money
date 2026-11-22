"""Unit tests for Money Manager financial calculations and CSV validation."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from services.data_loader import (
    load_all_data,
    load_debts,
    load_savings,
    load_transactions,
)
from services.finance import (
    build_dashboard_snapshot,
    calculate_monthly_comparison,
    calculate_monthly_summary,
    calculate_total_outstanding_debt,
    calculate_total_savings_balance,
    check_data_freshness,
    format_inr,
    format_period_label,
    get_latest_debt_balances,
    get_latest_savings_balances,
    get_latest_transaction_period,
)


# ---------------------------------------------------------------------------
# Indian Rupee Formatting
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("amount", "expected"),
    [
        (0, "₹0"),
        (500, "₹500"),
        (1000, "₹1,000"),
        (85000, "₹85,000"),
        (100000, "₹1,00,000"),
        (450000, "₹4,50,000"),
        (1250000, "₹12,50,000"),
        (12345678, "₹1,23,45,678"),
        (-15000, "-₹15,000"),
        (-1250000, "-₹12,50,000"),
        (1250.5, "₹1,250.50"),
        (85000.00, "₹85,000"),
    ],
)
def test_format_inr(amount: float | int, expected: str) -> None:
    assert format_inr(amount) == expected


# ---------------------------------------------------------------------------
# Latest-Month Selection
# ---------------------------------------------------------------------------


def test_get_latest_transaction_period_selects_most_recent_month() -> None:
    df = pd.DataFrame(
        [
            {"date": "2026-09-15", "type": "income", "amount": 85000, "description": "Salary"},
            {"date": "2026-10-04", "type": "expense", "amount": 16500, "description": "Groceries"},
            {"date": "2026-08-01", "type": "income", "amount": 85000, "description": "Salary"},
        ]
    )
    latest = get_latest_transaction_period(df)
    assert latest == pd.Period("2026-10", freq="M")
    assert format_period_label(latest) == "October 2026"


def test_get_latest_transaction_period_updates_when_new_month_added() -> None:
    df = pd.DataFrame(
        [
            {"date": "2026-10-01", "type": "income", "amount": 85000, "description": "Salary"},
            {"date": "2026-11-01", "type": "income", "amount": 90000, "description": "Salary"},
        ]
    )
    assert get_latest_transaction_period(df) == pd.Period("2026-11", freq="M")


def test_get_latest_transaction_period_returns_none_when_empty() -> None:
    empty_df = pd.DataFrame(columns=["date", "type", "amount", "description"])
    assert get_latest_transaction_period(empty_df) is None


# ---------------------------------------------------------------------------
# Monthly Income, Expenses, and Savings Calculations
# ---------------------------------------------------------------------------


def test_calculate_monthly_summary_defaults_to_latest_month() -> None:
    df = pd.DataFrame(
        [
            {"date": "2026-09-01", "type": "income", "amount": 80000, "description": "Salary"},
            {"date": "2026-09-05", "type": "expense", "amount": 50000, "description": "Expenses"},
            {"date": "2026-10-01", "type": "income", "amount": 90000, "description": "Salary"},
            {"date": "2026-10-12", "type": "income", "amount": 10000, "description": "Bonus"},
            {"date": "2026-10-04", "type": "expense", "amount": 22000, "description": "Rent"},
            {"date": "2026-10-15", "type": "expense", "amount": 18000, "description": "Groceries"},
        ]
    )

    summary = calculate_monthly_summary(df)
    assert summary.has_data is True
    assert summary.period == pd.Period("2026-10", freq="M")
    assert summary.monthly_income == pytest.approx(100000.0)
    assert summary.monthly_expenses == pytest.approx(40000.0)
    assert summary.monthly_savings == pytest.approx(60000.0)
    assert summary.transaction_count == 4


def test_calculate_monthly_summary_handles_negative_savings() -> None:
    df = pd.DataFrame(
        [
            {"date": "2026-10-01", "type": "income", "amount": 50000, "description": "Salary"},
            {"date": "2026-10-10", "type": "expense", "amount": 65000, "description": "Emergency repair"},
        ]
    )

    summary = calculate_monthly_summary(df)
    assert summary.monthly_income == pytest.approx(50000.0)
    assert summary.monthly_expenses == pytest.approx(65000.0)
    assert summary.monthly_savings == pytest.approx(-15000.0)


def test_calculate_monthly_summary_empty_transactions() -> None:
    empty_df = pd.DataFrame(columns=["date", "type", "amount", "description"])
    summary = calculate_monthly_summary(empty_df)
    assert summary.has_data is False
    assert summary.period is None
    assert summary.monthly_income == 0.0
    assert summary.monthly_expenses == 0.0
    assert summary.monthly_savings == 0.0


def test_calculate_monthly_comparison_chronological_all_months() -> None:
    df = pd.DataFrame(
        [
            {"date": "2026-10-01", "type": "income", "amount": 90000, "description": "Salary"},
            {"date": "2026-08-01", "type": "income", "amount": 85000, "description": "Salary"},
            {"date": "2026-08-05", "type": "expense", "amount": 40000, "description": "Rent"},
            {"date": "2026-09-10", "type": "expense", "amount": 25000, "description": "Bills"},
        ]
    )

    comparison = calculate_monthly_comparison(df)
    assert list(comparison["month_label"]) == ["Aug 2026", "Sep 2026", "Oct 2026"]
    assert list(comparison["income"]) == [85000.0, 0.0, 90000.0]
    assert list(comparison["expenses"]) == [40000.0, 25000.0, 0.0]
    assert list(comparison["savings"]) == [45000.0, -25000.0, 90000.0]


# ---------------------------------------------------------------------------
# Latest Savings Balance Per Account & Latest Debt Balance Per Loan
# ---------------------------------------------------------------------------


def test_latest_savings_balance_uses_only_latest_snapshot_per_account() -> None:
    savings_df = pd.DataFrame(
        [
            {"date": "2026-09-30", "account": "Primary savings", "balance": 130000},
            {"date": "2026-10-31", "account": "Primary savings", "balance": 142000},
            {"date": "2026-11-20", "account": "Primary savings", "balance": 158500},
            {"date": "2026-10-31", "account": "Emergency savings", "balance": 50000},
            {"date": "2026-11-20", "account": "Emergency savings", "balance": 55000},
            {"date": "2026-10-15", "account": "Fixed deposit", "balance": 200000},
        ]
    )

    latest = get_latest_savings_balances(savings_df)
    balances_by_account = dict(zip(latest["account"], latest["balance"]))

    assert balances_by_account == {
        "Primary savings": 158500.0,
        "Emergency savings": 55000.0,
        "Fixed deposit": 200000.0,
    }
    assert calculate_total_savings_balance(savings_df) == pytest.approx(413500.0)


def test_latest_debt_balance_uses_only_latest_snapshot_per_loan() -> None:
    debts_df = pd.DataFrame(
        [
            {"date": "2026-09-30", "loan": "Personal loan", "outstanding_balance": 320000},
            {"date": "2026-10-31", "loan": "Personal loan", "outstanding_balance": 310000},
            {"date": "2026-11-20", "loan": "Personal loan", "outstanding_balance": 300000},
            {"date": "2026-10-31", "loan": "Gold loan", "outstanding_balance": 45000},
            {"date": "2026-11-20", "loan": "Gold loan", "outstanding_balance": 40000},
            {"date": "2026-10-15", "loan": "Education loan", "outstanding_balance": 0},
        ]
    )

    latest = get_latest_debt_balances(debts_df)
    balances_by_loan = dict(zip(latest["loan"], latest["outstanding_balance"]))

    assert balances_by_loan == {
        "Personal loan": 300000.0,
        "Gold loan": 40000.0,
        "Education loan": 0.0,
    }
    assert calculate_total_outstanding_debt(debts_df) == pytest.approx(340000.0)


# ---------------------------------------------------------------------------
# Data Freshness Warning Logic
# ---------------------------------------------------------------------------


def test_data_freshness_warns_when_current_month_missing() -> None:
    latest = pd.Period("2026-10", freq="M")
    status = check_data_freshness(latest, reference_date=date(2026, 11, 21))

    assert status.has_data is True
    assert status.is_outdated is True
    assert status.latest_period == latest
    assert status.current_period == pd.Period("2026-11", freq="M")
    assert status.message == (
        "Data may be outdated. No transaction data is available for November 2026. "
        "The latest available data is for October 2026. "
        "Showing October's figures below."
    )


def test_data_freshness_clears_warning_when_current_month_present() -> None:
    latest = pd.Period("2026-11", freq="M")
    status = check_data_freshness(latest, reference_date=date(2026, 11, 21))

    assert status.has_data is True
    assert status.is_outdated is False
    assert status.message is None


def test_data_freshness_handles_cross_year_boundary() -> None:
    latest = pd.Period("2025-12", freq="M")
    status = check_data_freshness(latest, reference_date=date(2026, 1, 5))

    assert status.is_outdated is True
    assert "January 2026" in (status.message or "")
    assert "December 2025" in (status.message or "")


def test_data_freshness_handles_empty_transactions() -> None:
    status = check_data_freshness(None, reference_date=date(2026, 11, 21))

    assert status.has_data is False
    assert status.is_outdated is False
    assert status.message is not None
    assert "No transaction data is available" in status.message


def test_dashboard_snapshot_keeps_latest_month_figures_when_outdated() -> None:
    transactions_df = pd.DataFrame(
        [
            {"date": "2026-10-01", "type": "income", "amount": 90000, "description": "Salary"},
            {"date": "2026-10-05", "type": "expense", "amount": 35000, "description": "Rent & food"},
        ]
    )
    savings_df = pd.DataFrame(
        [{"date": "2026-11-15", "account": "Primary", "balance": 150000}]
    )
    debts_df = pd.DataFrame(
        [{"date": "2026-11-15", "loan": "Car loan", "outstanding_balance": 200000}]
    )

    snapshot = build_dashboard_snapshot(
        transactions_df=transactions_df,
        savings_df=savings_df,
        debts_df=debts_df,
        reference_date=date(2026, 11, 21),
    )

    assert snapshot.freshness.is_outdated is True
    assert snapshot.selected_period == pd.Period("2026-10", freq="M")
    assert snapshot.monthly_summary.monthly_income == pytest.approx(90000.0)
    assert snapshot.monthly_summary.monthly_expenses == pytest.approx(35000.0)
    assert snapshot.monthly_summary.monthly_savings == pytest.approx(55000.0)
    assert snapshot.total_savings_balance == pytest.approx(150000.0)
    assert snapshot.total_outstanding_debt == pytest.approx(200000.0)


# ---------------------------------------------------------------------------
# CSV Loading and Input Validation
# ---------------------------------------------------------------------------


def test_load_transactions_handles_missing_file(tmp_path: Path) -> None:
    result = load_transactions(tmp_path / "does_not_exist.csv")
    assert result.is_missing is True
    assert result.has_data is False
    assert result.error is not None
    assert "not found" in result.error.lower()


def test_load_transactions_handles_empty_and_header_only_files(tmp_path: Path) -> None:
    empty_file = tmp_path / "empty.csv"
    empty_file.write_text("", encoding="utf-8")
    empty_result = load_transactions(empty_file)
    assert empty_result.is_empty is True
    assert empty_result.error is None
    assert empty_result.df.empty

    header_only = tmp_path / "header_only.csv"
    header_only.write_text("date,type,amount,description\n", encoding="utf-8")
    header_result = load_transactions(header_only)
    assert header_result.is_empty is True
    assert header_result.error is None
    assert header_result.df.empty


def test_load_transactions_reports_missing_required_columns(tmp_path: Path) -> None:
    bad_schema = tmp_path / "transactions.csv"
    bad_schema.write_text("date,amount,description\n2026-10-01,5000,Salary\n", encoding="utf-8")

    result = load_transactions(bad_schema)
    assert result.error is not None
    assert "type" in result.error
    assert result.df.empty


def test_load_transactions_validates_rows_and_skips_invalid_records(tmp_path: Path) -> None:
    csv_file = tmp_path / "transactions.csv"
    csv_file.write_text(
        "\n".join(
            [
                "date,type,amount,description",
                "2026-10-01,INCOME,90000,Monthly salary",
                "2026-10-01,income,90000,Monthly salary",  # exact duplicate
                "not-a-date,expense,5000,Bad date",
                "2026-10-05,transfer,10000,Invalid type",
                "2026-10-06,expense,-2000,Negative amount",
                "2026-10-07,expense,0,Zero amount",
                "2026-10-08,expense,abc,Non numeric amount",
                "2026-10-09,expense,12000,Rent,ExtraMalformedColumn",
                "2026-10-10,expense,18000,Groceries",
            ]
        ),
        encoding="utf-8",
    )

    result = load_transactions(csv_file)
    assert result.error is None
    assert len(result.df) == 2
    assert list(result.df["type"]) == ["income", "expense"]
    assert list(result.df["amount"]) == [90000.0, 18000.0]
    assert len(result.warnings) >= 5


def test_load_savings_and_debts_validation_and_deduplication(tmp_path: Path) -> None:
    savings_file = tmp_path / "savings.csv"
    savings_file.write_text(
        "\n".join(
            [
                "date,account,balance",
                "2026-10-31,Primary savings,140000",
                "2026-10-31,Primary savings,142000",  # same-day update
                "2026-10-31,,50000",  # missing account
                "2026-10-31,Invalid balance,-100",
                "bad-date,Emergency fund,50000",
                "2026-11-15,Emergency fund,0",  # zero balance is valid
            ]
        ),
        encoding="utf-8",
    )

    debts_file = tmp_path / "debts.csv"
    debts_file.write_text(
        "\n".join(
            [
                "date,loan,outstanding_balance",
                "2026-10-31,Personal loan,310000",
                "2026-10-31,Personal loan,310000",  # exact duplicate
                "2026-11-15,Personal loan,300000",
                "2026-11-15,Gold loan,not_a_number",
            ]
        ),
        encoding="utf-8",
    )

    savings_res = load_savings(savings_file)
    assert savings_res.error is None
    assert len(savings_res.df) == 2
    assert calculate_total_savings_balance(savings_res.df) == pytest.approx(142000.0)
    assert len(savings_res.warnings) >= 4

    debts_res = load_debts(debts_file)
    assert debts_res.error is None
    assert len(debts_res.df) == 2
    assert calculate_total_outstanding_debt(debts_res.df) == pytest.approx(300000.0)
    assert len(debts_res.warnings) >= 2


def test_repository_sample_data_loads_cleanly() -> None:
    data_dir = Path(__file__).resolve().parent.parent / "data"
    bundle = load_all_data(data_dir)

    assert bundle.errors == []
    assert bundle.warnings == []
    assert bundle.transactions.has_data is True
    assert bundle.savings.has_data is True
    assert bundle.debts.has_data is True

    comparison = calculate_monthly_comparison(bundle.transactions.df)
    assert len(comparison) >= 6
