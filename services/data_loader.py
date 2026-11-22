"""CSV loading and validation services for Money Manager.

This module isolates all filesystem and CSV parsing logic from both the
financial calculation engine and the Streamlit UI. In future versions, the
functions here can be swapped for or backed by a relational database or API
repository while preserving the normalized DataFrame contracts.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

TRANSACTION_COLUMNS = ("date", "type", "amount", "description")
SAVINGS_COLUMNS = ("date", "account", "balance")
DEBTS_COLUMNS = ("date", "loan", "outstanding_balance")
VALID_TRANSACTION_TYPES = frozenset({"income", "expense"})


@dataclass(frozen=True)
class LoadResult:
    """Normalized result returned by each CSV loader."""

    df: pd.DataFrame
    warnings: tuple[str, ...] = field(default_factory=tuple)
    error: str | None = None
    is_missing: bool = False
    is_empty: bool = False

    @property
    def has_data(self) -> bool:
        """Return True when at least one valid record was loaded."""
        return not self.df.empty


@dataclass(frozen=True)
class DataBundle:
    """Container holding all validated datasets required by the dashboard."""

    transactions: LoadResult
    savings: LoadResult
    debts: LoadResult

    @property
    def errors(self) -> list[str]:
        """Collect all fatal file-level errors across datasets."""
        return [
            result.error
            for result in (self.transactions, self.savings, self.debts)
            if result.error
        ]

    @property
    def warnings(self) -> list[str]:
        """Collect all non-fatal row validation warnings across datasets."""
        all_warnings: list[str] = []
        for result in (self.transactions, self.savings, self.debts):
            all_warnings.extend(result.warnings)
        return all_warnings


def _empty_frame(columns: tuple[str, ...]) -> pd.DataFrame:
    """Return an empty DataFrame with canonical column names."""
    return pd.DataFrame(columns=list(columns))


def _read_raw_csv(
    file_path: Path,
    required_columns: tuple[str, ...],
    dataset_label: str,
) -> tuple[pd.DataFrame | None, list[str], str | None, bool, bool]:
    """Read a CSV file safely and check structural integrity.

    Returns:
        (raw_df, warnings, error, is_missing, is_empty)
    """
    warnings: list[str] = []

    if not file_path.exists():
        return (
            None,
            warnings,
            f"{dataset_label} file not found at '{file_path}'. Please create it with columns: {', '.join(required_columns)}.",
            True,
            True,
        )

    if not file_path.is_file():
        return (
            None,
            warnings,
            f"Expected '{file_path}' to be a CSV file, but it is not a regular file.",
            False,
            True,
        )

    try:
        raw_text = file_path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        return (
            None,
            warnings,
            f"Could not read {dataset_label} file '{file_path}': {exc}",
            False,
            True,
        )

    if not raw_text.strip():
        return (None, warnings, None, False, True)

    # Parse via Python's csv.reader first so malformed rows with extra or
    # missing columns are skipped cleanly with an explicit user-facing count.
    try:
        rows = list(csv.reader(raw_text.splitlines()))
    except csv.Error as exc:
        return (
            None,
            warnings,
            f"{dataset_label} file '{file_path.name}' contains unreadable CSV syntax: {exc}",
            False,
            True,
        )

    non_blank_rows = [row for row in rows if any(cell.strip() for cell in row)]
    if not non_blank_rows:
        return (None, warnings, None, False, True)

    headers = [col.strip().lower() for col in non_blank_rows[0]]
    missing_cols = [col for col in required_columns if col not in headers]
    if missing_cols:
        return (
            None,
            warnings,
            f"{dataset_label} file '{file_path.name}' is missing required column(s): {', '.join(missing_cols)}.",
            False,
            True,
        )

    if len(headers) != len(set(headers)):
        return (
            None,
            warnings,
            f"{dataset_label} file '{file_path.name}' contains duplicate column headers.",
            False,
            True,
        )

    data_rows = non_blank_rows[1:]
    if not data_rows:
        return (None, warnings, None, False, True)

    expected_width = len(headers)
    valid_width_rows: list[list[str]] = []
    malformed_count = 0

    for row in data_rows:
        if len(row) != expected_width:
            malformed_count += 1
            continue
        valid_width_rows.append([cell.strip() for cell in row])

    if malformed_count:
        warnings.append(
            f"{file_path.name}: Skipped {malformed_count} malformed record(s) with an unexpected number of columns."
        )

    if not valid_width_rows:
        return (None, warnings, None, False, True)

    raw_df = pd.DataFrame(valid_width_rows, columns=headers)
    return (raw_df, warnings, None, False, False)


def _parse_dates(series: pd.Series) -> pd.Series:
    """Parse date strings strictly while tolerating standard ISO formatting."""
    return pd.to_datetime(series, errors="coerce", format="mixed")


def load_transactions(file_path: str | Path) -> LoadResult:
    """Load and validate income/expense transactions from transactions.csv.

    Validation rules:
    - Required columns: date, type, amount, description.
    - Dates must parse cleanly.
    - Type must be 'income' or 'expense' (case-insensitive).
    - Amount must be a valid finite number strictly greater than zero.
    - Exact duplicate records are removed with a warning.
    """
    path = Path(file_path)
    raw_df, warnings, error, is_missing, is_empty = _read_raw_csv(
        path, TRANSACTION_COLUMNS, "Transactions"
    )
    if error or raw_df is None:
        return LoadResult(
            df=_empty_frame(TRANSACTION_COLUMNS),
            warnings=tuple(warnings),
            error=error,
            is_missing=is_missing,
            is_empty=is_empty,
        )

    df = raw_df.copy()

    # Validate dates
    df["date"] = _parse_dates(df["date"])
    invalid_date_mask = df["date"].isna()
    if invalid_date_mask.any():
        count = int(invalid_date_mask.sum())
        warnings.append(
            f"{path.name}: Skipped {count} record(s) with invalid or missing dates."
        )
        df = df.loc[~invalid_date_mask].copy()

    # Validate transaction type
    df["type"] = df["type"].astype(str).str.strip().str.lower()
    invalid_type_mask = ~df["type"].isin(VALID_TRANSACTION_TYPES)
    if invalid_type_mask.any():
        count = int(invalid_type_mask.sum())
        warnings.append(
            f"{path.name}: Skipped {count} record(s) with invalid transaction type (expected 'income' or 'expense')."
        )
        df = df.loc[~invalid_type_mask].copy()

    # Validate positive finite numeric amounts
    cleaned_amounts = df["amount"].astype(str).str.replace(",", "", regex=False).str.strip()
    df["amount"] = pd.to_numeric(cleaned_amounts, errors="coerce")
    invalid_amount_mask = (
        df["amount"].isna()
        | df["amount"].isin([float("inf"), float("-inf")])
        | (df["amount"] <= 0)
    )
    if invalid_amount_mask.any():
        count = int(invalid_amount_mask.sum())
        warnings.append(
            f"{path.name}: Skipped {count} record(s) with missing, non-numeric, or non-positive amounts."
        )
        df = df.loc[~invalid_amount_mask].copy()

    # Normalize description (fill empty descriptions cleanly)
    df["description"] = df["description"].fillna("").astype(str).str.strip()
    df.loc[df["description"] == "", "description"] = "Unspecified"

    # Remove exact duplicate rows
    before_dedup = len(df)
    df = df.drop_duplicates(subset=list(TRANSACTION_COLUMNS), keep="first")
    duplicate_count = before_dedup - len(df)
    if duplicate_count > 0:
        warnings.append(
            f"{path.name}: Ignored {duplicate_count} exact duplicate transaction record(s)."
        )

    if df.empty:
        return LoadResult(
            df=_empty_frame(TRANSACTION_COLUMNS),
            warnings=tuple(warnings),
            error=None,
            is_missing=False,
            is_empty=True,
        )

    df = df.sort_values(by="date", kind="mergesort").reset_index(drop=True)
    return LoadResult(
        df=df,
        warnings=tuple(warnings),
        error=None,
        is_missing=False,
        is_empty=False,
    )


def _load_balance_snapshots(
    file_path: str | Path,
    required_columns: tuple[str, str, str],
    entity_col: str,
    value_col: str,
    dataset_label: str,
) -> LoadResult:
    """Shared validator for point-in-time snapshot tables (savings and debts).

    Validation rules:
    - Required columns: (date, entity_col, value_col).
    - Dates must parse cleanly.
    - Entity name (account or loan) must be non-empty.
    - Balance must be a valid finite number >= 0.
    - Exact duplicate records and duplicate same-day snapshots are handled cleanly.
    """
    path = Path(file_path)
    raw_df, warnings, error, is_missing, is_empty = _read_raw_csv(
        path, required_columns, dataset_label
    )
    if error or raw_df is None:
        return LoadResult(
            df=_empty_frame(required_columns),
            warnings=tuple(warnings),
            error=error,
            is_missing=is_missing,
            is_empty=is_empty,
        )

    df = raw_df.copy()

    # Validate dates
    df["date"] = _parse_dates(df["date"])
    invalid_date_mask = df["date"].isna()
    if invalid_date_mask.any():
        count = int(invalid_date_mask.sum())
        warnings.append(
            f"{path.name}: Skipped {count} record(s) with invalid or missing dates."
        )
        df = df.loc[~invalid_date_mask].copy()

    # Validate entity name (account / loan)
    df[entity_col] = df[entity_col].fillna("").astype(str).str.strip()
    invalid_entity_mask = df[entity_col] == ""
    if invalid_entity_mask.any():
        count = int(invalid_entity_mask.sum())
        warnings.append(
            f"{path.name}: Skipped {count} record(s) with a missing {entity_col} name."
        )
        df = df.loc[~invalid_entity_mask].copy()

    # Validate non-negative finite balance
    cleaned_values = df[value_col].astype(str).str.replace(",", "", regex=False).str.strip()
    df[value_col] = pd.to_numeric(cleaned_values, errors="coerce")
    invalid_value_mask = (
        df[value_col].isna()
        | df[value_col].isin([float("inf"), float("-inf")])
        | (df[value_col] < 0)
    )
    if invalid_value_mask.any():
        count = int(invalid_value_mask.sum())
        warnings.append(
            f"{path.name}: Skipped {count} record(s) with missing, non-numeric, or negative {value_col.replace('_', ' ')}."
        )
        df = df.loc[~invalid_value_mask].copy()

    # Deduplicate exact duplicates first
    before_exact = len(df)
    df = df.drop_duplicates(subset=list(required_columns), keep="last")
    exact_dups = before_exact - len(df)
    if exact_dups > 0:
        warnings.append(
            f"{path.name}: Ignored {exact_dups} exact duplicate snapshot record(s)."
        )

    # Deduplicate conflicting snapshots on the same (date, entity), keeping latest entry
    before_same_day = len(df)
    df = df.drop_duplicates(subset=["date", entity_col], keep="last")
    same_day_dups = before_same_day - len(df)
    if same_day_dups > 0:
        warnings.append(
            f"{path.name}: Found {same_day_dups} duplicate same-day snapshot(s) for the same {entity_col}; kept the latest entry."
        )

    if df.empty:
        return LoadResult(
            df=_empty_frame(required_columns),
            warnings=tuple(warnings),
            error=None,
            is_missing=False,
            is_empty=True,
        )

    df = df.sort_values(by=["date", entity_col], kind="mergesort").reset_index(drop=True)
    return LoadResult(
        df=df,
        warnings=tuple(warnings),
        error=None,
        is_missing=False,
        is_empty=False,
    )


def load_savings(file_path: str | Path) -> LoadResult:
    """Load and validate savings balance snapshots from savings.csv."""
    return _load_balance_snapshots(
        file_path=file_path,
        required_columns=SAVINGS_COLUMNS,
        entity_col="account",
        value_col="balance",
        dataset_label="Savings",
    )


def load_debts(file_path: str | Path) -> LoadResult:
    """Load and validate loan outstanding balance snapshots from debts.csv."""
    return _load_balance_snapshots(
        file_path=file_path,
        required_columns=DEBTS_COLUMNS,
        entity_col="loan",
        value_col="outstanding_balance",
        dataset_label="Debts",
    )


def load_all_data(data_dir: str | Path) -> DataBundle:
    """Load transactions, savings, and debts CSV files from a data directory."""
    base_path = Path(data_dir)
    return DataBundle(
        transactions=load_transactions(base_path / "transactions.csv"),
        savings=load_savings(base_path / "savings.csv"),
        debts=load_debts(base_path / "debts.csv"),
    )
