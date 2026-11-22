# Money Manager (Version 1)

**Money Manager** is a clean, offline-first personal finance dashboard built with **Python**, **Streamlit**, **Pandas**, **Plotly**, and **Pytest**.

All financial data is read locally from simple CSV files in `data/`, with zero external APIs, zero cloud dependencies, and zero internet access required once Python packages are installed.

---

## Features

- **Single-page calm dashboard** with rounded summary cards, Indian Rupee (`₹`) formatting using Indian number grouping (e.g., `₹85,000`, `₹4,50,000`, `₹12,50,000`), and responsive desktop/mobile layout.
- **Automatic month selection** that always detects the latest transaction month in `data/transactions.csv` without hardcoding dates.
- **Data freshness warning** that compares your computer's current month against the latest month in `data/transactions.csv`, displaying an amber banner when current-month data is missing while continuing to show the latest available month's figures. The warning disappears automatically as soon as current-month transactions are added.
- **Five distinct financial summary cards**:
  1. **Monthly Income**
  2. **Monthly Expenses**
  3. **Monthly Savings** (`Monthly Income − Monthly Expenses`)
  4. **Current Savings Balance** (sum of the latest dated balance per savings account)
  5. **Outstanding Debt** (sum of the latest dated outstanding balance per loan)
- **Interactive Income vs. Expenses chart** built with Plotly across all recorded months, with INR formatting and unified hover tooltips.
- **Defensive input validation** handling missing files, empty files, invalid dates, unknown transaction types, non-positive amounts, malformed CSV lines, and duplicate rows gracefully.

---

## Project Structure

```text
money-manager/
├── app.py                  # Streamlit dashboard UI
├── requirements.txt        # Python dependencies
├── README.md               # Documentation
├── .streamlit/
│   └── config.toml         # Light theme configuration
├── data/
│   ├── transactions.csv    # Monthly income & expense transactions
│   ├── savings.csv         # Point-in-time savings account balance snapshots
│   └── debts.csv           # Point-in-time loan outstanding balance snapshots
├── services/
│   ├── __init__.py
│   ├── data_loader.py      # CSV loading & input validation
│   └── finance.py          # Pure financial calculations & INR formatting
└── tests/
    ├── __init__.py
    └── test_finance.py     # Pytest unit tests
```

---

## Prerequisites

- **Python 3.10+** (tested for Python 3.11 / 3.12+)
- `pip`

---

## Installation & Running Locally

1. **(Optional) Create and activate a virtual environment:**

   ```bash
   python -m venv .venv
   source .venv/bin/activate        # macOS / Linux
   #  .\.venv\Scripts\Activate.ps1       # Windows
   ```

2. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

3. **Launch the Streamlit dashboard:**

   ```bash
   streamlit run app.py
   ```

4. **Run the unit test suite:**

   ```bash
   pytest
   ```

---

## CSV Data Formats

All sample data included in `data/` is fictional.

### `data/transactions.csv`
Records individual income and expense transactions (positive amounts only).

```csv
date,type,amount,description
2026-09-01,income,90000,Monthly salary
2026-09-04,expense,18000,Household and groceries
```

- `date`: ISO date (`YYYY-MM-DD`)
- `type`: `income` or `expense`
- `amount`: Positive number
- `description`: Short text note

### `data/savings.csv`
Records point-in-time balance snapshots per savings account. The dashboard automatically picks **only the latest dated snapshot for each account** and never sums historical snapshots.

```csv
date,account,balance
2026-10-31,Primary savings,142000
2026-11-18,Primary savings,158500
2026-11-18,Emergency fund,60000
```

### `data/debts.csv`
Records point-in-time outstanding loan balance snapshots. The dashboard automatically picks **only the latest dated balance for each loan** and never sums historical snapshots.

```csv
date,loan,outstanding_balance
2026-10-31,Personal loan,305000
2026-11-18,Personal loan,300000
2026-11-18,Gold loan,40000
```

---

## Architecture & Future Extensibility

Financial logic (`services/finance.py`) and data access (`services/data_loader.py`) are completely decoupled from Streamlit (`app.py`). This modular foundation is designed to support future versions cleanly, including:

- Multiple family members and individual vs. shared expenses
- Expense categories, monthly budgets, and savings goals
- Loan repayment schedules and payoff tracking
- Authentication, permissions, relational database storage, and a Python API backend for mobile apps
