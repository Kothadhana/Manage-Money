"""Money Manager — Version 1 Personal Finance Dashboard (Streamlit)."""

from __future__ import annotations

import html
import math
from pathlib import Path
from textwrap import dedent

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


from services.data_loader import DataBundle, load_all_data
from services.finance import (
    DashboardSnapshot,
    build_dashboard_snapshot,
    format_inr,
    format_period_label,
)

DATA_DIR = Path(__file__).resolve().parent / "data"

INCOME_COLOR = "#2F9E66"
EXPENSE_COLOR = "#C85A54"
SAVINGS_BALANCE_COLOR = "#2B6CB0"
DEBT_COLOR = "#B8524C"


def inject_styles() -> None:
    """Apply a calm, modern, responsive light theme with offline-safe system fonts."""
    st.markdown(
        """
        <style>
            :root {
                --bg-page: #F6F8FA;
                --bg-card: #FFFFFF;
                --border-subtle: #E5E9F0;
                --text-primary: #0F172A;
                --text-secondary: #526071;
                --text-muted: #7B8794;
                --accent-green: #1E8E5A;
                --accent-blue: #2B6CB0;
                --accent-red: #B8524C;
                --amber-bg: #FFFBEB;
                --amber-border: #F59E0B;
                --amber-stroke: #FDE68A;
                --amber-text: #92400E;
            }

            html, body, [class*="css"] {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
                             "Helvetica Neue", Arial, sans-serif;
            }

            .stApp {
                background-color: var(--bg-page);
                color: var(--text-primary);
            }

            /* Hide sidebar and default chrome for a focused single-page dashboard */
            [data-testid="stSidebar"],
            [data-testid="collapsedControl"],
            #MainMenu,
            footer,
            header[data-testid="stHeader"] {
                display: none !important;
            }

            .block-container {
                max-width: 1200px;
                padding-top: 2rem;
                padding-bottom: 3rem;
                padding-left: 1.5rem;
                padding-right: 1.5rem;
            }

            /* Header */
            .mm-header {
                display: flex;
                flex-wrap: wrap;
                align-items: flex-end;
                justify-content: space-between;
                gap: 1rem;
                margin-bottom: 1.25rem;
                padding-bottom: 1rem;
                border-bottom: 1px solid var(--border-subtle);
            }

            .mm-title {
                margin: 0;
                font-size: 1.95rem;
                font-weight: 700;
                letter-spacing: -0.025em;
                color: var(--text-primary);
                line-height: 1.2;
            }

            .mm-subtitle {
                margin: 0.25rem 0 0 0;
                font-size: 0.98rem;
                color: var(--text-secondary);
                font-weight: 400;
            }

            .mm-period-box {
                background: var(--bg-card);
                border: 1px solid var(--border-subtle);
                border-radius: 12px;
                padding: 0.6rem 1rem;
                box-shadow: 0 1px 4px rgba(15, 23, 42, 0.04);
                text-align: right;
            }

            .mm-period-label {
                display: block;
                font-size: 0.72rem;
                text-transform: uppercase;
                letter-spacing: 0.06em;
                color: var(--text-muted);
                font-weight: 600;
            }

            .mm-period-value {
                display: block;
                font-size: 1.02rem;
                font-weight: 600;
                color: var(--text-primary);
                margin-top: 0.1rem;
            }

            /* Amber freshness warning banner */
            .mm-warning-banner {
                display: flex;
                align-items: flex-start;
                gap: 0.75rem;
                background-color: var(--amber-bg);
                border: 1px solid var(--amber-stroke);
                border-left: 4px solid var(--amber-border);
                border-radius: 12px;
                padding: 0.95rem 1.15rem;
                margin-bottom: 1.35rem;
                color: var(--amber-text);
                box-shadow: 0 2px 6px rgba(245, 158, 11, 0.08);
            }

            .mm-warning-icon {
                font-size: 1.1rem;
                line-height: 1.4;
                flex-shrink: 0;
            }

            .mm-warning-text {
                font-size: 0.94rem;
                line-height: 1.5;
                font-weight: 500;
                margin: 0;
            }

            /* Empty / info state banner */
            .mm-empty-banner {
                background: #EFF6FF;
                border: 1px solid #BFDBFE;
                border-left: 4px solid var(--accent-blue);
                border-radius: 12px;
                padding: 1rem 1.2rem;
                margin-bottom: 1.35rem;
                color: #1E3A8A;
                font-size: 0.95rem;
                line-height: 1.5;
            }

            /* Responsive 5-card grid */
            .mm-card-grid {
                display: grid;
                grid-template-columns: repeat(5, minmax(0, 1fr));
                gap: 1rem;
                margin-bottom: 1.5rem;
            }

            @media (max-width: 1120px) {
                .mm-card-grid {
                    grid-template-columns: repeat(3, minmax(0, 1fr));
                }
            }

            @media (max-width: 740px) {
                .mm-card-grid {
                    grid-template-columns: repeat(2, minmax(0, 1fr));
                }
                .mm-period-box {
                    text-align: left;
                }
            }

            @media (max-width: 480px) {
                .mm-card-grid {
                    grid-template-columns: 1fr;
                }
                .block-container {
                    padding-left: 1rem;
                    padding-right: 1rem;
                }
            }

            .mm-card {
                background: var(--bg-card);
                border: 1px solid var(--border-subtle);
                border-top: 3px solid var(--card-accent, var(--accent-blue));
                border-radius: 14px;
                padding: 1.15rem 1.2rem;
                box-shadow: 0 2px 10px rgba(15, 23, 42, 0.04);
                display: flex;
                flex-direction: column;
                justify-content: space-between;
                min-height: 126px;
            }

            .mm-card-title {
                font-size: 0.84rem;
                font-weight: 600;
                color: var(--text-secondary);
                margin: 0;
                line-height: 1.3;
            }

            .mm-card-value {
                font-size: 1.6rem;
                font-weight: 700;
                color: var(--card-value-color, var(--text-primary));
                font-variant-numeric: tabular-nums;
                letter-spacing: -0.02em;
                margin: 0.55rem 0 0.45rem 0;
                line-height: 1.15;
                word-break: break-word;
            }

            .mm-card-caption {
                font-size: 0.78rem;
                color: var(--text-muted);
                margin: 0;
                line-height: 1.35;
            }

            /* Section container cards */
            .mm-section-card,
            div[data-testid="stVerticalBlockBorderWrapper"] {
                background: var(--bg-card) !important;
                border: 1px solid var(--border-subtle) !important;
                border-radius: 16px !important;
                box-shadow: 0 2px 10px rgba(15, 23, 42, 0.04) !important;
            }

            .mm-section-card {
                padding: 1.25rem 1.35rem;
                margin-bottom: 1.35rem;
            }

            div[data-testid="stVerticalBlockBorderWrapper"] {
                padding: 0.45rem 0.65rem 0.25rem 0.65rem !important;
                margin-bottom: 1.35rem !important;
            }

            .mm-section-title {
                font-size: 1.08rem;
                font-weight: 650;
                color: var(--text-primary);
                margin: 0;
            }

            .mm-section-subtitle {
                font-size: 0.86rem;
                color: var(--text-muted);
                margin: 0.2rem 0 0.75rem 0;
            }

            /* Snapshot breakdown list */
            .mm-snapshot-grid {
                display: grid;
                grid-template-columns: repeat(2, minmax(0, 1fr));
                gap: 1.1rem;
                margin-top: 0.25rem;
            }

            @media (max-width: 760px) {
                .mm-snapshot-grid {
                    grid-template-columns: 1fr;
                }
            }

            .mm-list-row {
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 0.68rem 0;
                border-bottom: 1px solid #F1F5F9;
                gap: 0.75rem;
            }

            .mm-list-row:last-child {
                border-bottom: none;
                padding-bottom: 0.1rem;
            }

            .mm-list-name {
                font-size: 0.92rem;
                font-weight: 500;
                color: var(--text-primary);
            }

            .mm-list-date {
                font-size: 0.78rem;
                color: var(--text-muted);
                margin-top: 0.12rem;
            }

            .mm-list-amount {
                font-size: 0.96rem;
                font-weight: 600;
                font-variant-numeric: tabular-nums;
                white-space: nowrap;
            }

            .mm-empty-muted {
                font-size: 0.88rem;
                color: var(--text-muted);
                padding: 0.5rem 0 0.25rem 0;
                margin: 0;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header(snapshot: DashboardSnapshot) -> None:
    """Render application title, subtitle, and active data period."""
    period_text = (
        format_period_label(snapshot.selected_period)
        if snapshot.selected_period is not None
        else "No transaction data"
    )
    st.markdown(
        f"""
        <div class="mm-header">
            <div>
                <h1 class="mm-title">Money Manager</h1>
                <p class="mm-subtitle">Personal Finance Dashboard</p>
            </div>
            <div class="mm-period-box">
                <span class="mm-period-label">Current Data Period</span>
                <span class="mm-period-value">{html.escape(period_text)}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_freshness_and_notices(bundle: DataBundle, snapshot: DashboardSnapshot) -> None:
    """Render amber data freshness warning, empty states, and file validation alerts."""
    if snapshot.freshness.is_outdated and snapshot.freshness.message:
        st.markdown(
            f"""
            <div class="mm-warning-banner" role="alert">
                <div class="mm-warning-icon" aria-hidden="true">&#9888;</div>
                <p class="mm-warning-text">{html.escape(snapshot.freshness.message)}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    elif not snapshot.freshness.has_data and not bundle.transactions.error:
        no_data_msg = (
            snapshot.freshness.message
            or "No transaction data is available. Add records to data/transactions.csv to get started."
        )
        st.markdown(
            f"""
            <div class="mm-empty-banner" role="status">
                {html.escape(no_data_msg)}
            </div>
            """,
            unsafe_allow_html=True,
        )

    for error_msg in bundle.errors:
        st.error(error_msg)

    if bundle.warnings:
        with st.expander(
            f"Data validation notes ({len(bundle.warnings)})",
            expanded=False,
        ):
            for warning_msg in bundle.warnings:
                st.warning(warning_msg)


def render_summary_cards(snapshot: DashboardSnapshot) -> None:
    """Render the five core financial summary cards in Indian Rupee formatting."""
    summary = snapshot.monthly_summary
    has_tx = summary.has_data and summary.period is not None
    period_label = format_period_label(summary.period) if has_tx else "No transactions recorded"

    income_value = format_inr(summary.monthly_income) if has_tx else "—"
    expense_value = format_inr(summary.monthly_expenses) if has_tx else "—"
    savings_value = format_inr(summary.monthly_savings) if has_tx else "—"

    monthly_savings_accent = (
        INCOME_COLOR if (not has_tx or summary.monthly_savings >= 0) else EXPENSE_COLOR
    )
    monthly_savings_text = (
        "#1E7E4E" if (has_tx and summary.monthly_savings >= 0) else (
            "#B8524C" if has_tx else "#0F172A"
        )
    )

    savings_account_count = len(snapshot.latest_savings)
    savings_caption = (
        f"Latest balance across {savings_account_count} account"
        f"{'s' if savings_account_count != 1 else ''}"
        if savings_account_count > 0
        else "No savings snapshots recorded"
    )

    debt_loan_count = len(snapshot.latest_debts)
    debt_caption = (
        f"Latest balance across {debt_loan_count} loan"
        f"{'s' if debt_loan_count != 1 else ''}"
        if debt_loan_count > 0
        else "No loan snapshots recorded"
    )

    cards = [
        {
            "title": "Monthly Income",
            "value": income_value,
            "caption": period_label,
            "accent": INCOME_COLOR,
            "value_color": "#1E7E4E" if has_tx else "#64748B",
        },
        {
            "title": "Monthly Expenses",
            "value": expense_value,
            "caption": period_label,
            "accent": EXPENSE_COLOR,
            "value_color": "#B8524C" if has_tx else "#64748B",
        },
        {
            "title": "Monthly Savings",
            "value": savings_value,
            "caption": "Income minus expenses" if has_tx else "Awaiting monthly transactions",
            "accent": monthly_savings_accent,
            "value_color": monthly_savings_text if has_tx else "#64748B",
        },
        {
            "title": "Current Savings Balance",
            "value": format_inr(snapshot.total_savings_balance),
            "caption": savings_caption,
            "accent": SAVINGS_BALANCE_COLOR,
            "value_color": "#1E5693",
        },
        {
            "title": "Outstanding Debt",
            "value": format_inr(snapshot.total_outstanding_debt),
            "caption": debt_caption,
            "accent": DEBT_COLOR,
            "value_color": "#A3443F" if snapshot.total_outstanding_debt > 0 else "#1E7E4E",
        },
    ]

    card_html_parts = []

    for card in cards:
        card_html_parts.append(
            dedent(
                f"""
                <div class="mm-card" style="--mm-card-accent: {card['accent']}; --mm-card-value-color: {card['value_color']};">
                    <p class="mm-card-title">{html.escape(card['title'])}</p>
                    <p class="mm-card-value">{html.escape(card['value'])}</p>
                    <p class="mm-card-caption">{html.escape(card['caption'])}</p>
                </div>
                """
            )
        )

    st.markdown(
        f'<div class="mm-card-grid">{"".join(card_html_parts)}</div>',
        unsafe_allow_html=True,
    )


def _build_inr_yaxis_ticks(max_value: float) -> tuple[list[float], list[str]]:
    """Compute clean Indian-grouped INR tick marks for the Y-axis."""
    if max_value <= 0:
        return [0.0], ["₹0"]

    target_ticks = 5
    raw_step = max_value / target_ticks
    magnitude = 10 ** math.floor(math.log10(raw_step))
    residual = raw_step / magnitude

    if residual <= 1:
        nice_step = 1 * magnitude
    elif residual <= 2:
        nice_step = 2 * magnitude
    elif residual <= 2.5:
        nice_step = 2.5 * magnitude
    elif residual <= 5:
        nice_step = 5 * magnitude
    else:
        nice_step = 10 * magnitude

    upper = math.ceil(max_value / nice_step) * nice_step
    tick_vals: list[float] = []
    current = 0.0
    while current <= upper + (nice_step * 0.01):
        tick_vals.append(round(current, 2))
        current += nice_step

    tick_text = [format_inr(val) for val in tick_vals]
    return tick_vals, tick_text


def build_income_vs_expenses_chart(comparison_df: pd.DataFrame) -> go.Figure:
    """Create a responsive Plotly grouped bar chart comparing monthly income and expenses."""
    income_labels = [format_inr(v) for v in comparison_df["income"]]
    expense_labels = [format_inr(v) for v in comparison_df["expenses"]]
    savings_labels = [format_inr(v) for v in comparison_df["savings"]]
    full_months = comparison_df["month_full_label"].tolist()

    custom_income = list(zip(full_months, income_labels, savings_labels))
    custom_expense = list(zip(full_months, expense_labels, savings_labels))

    max_val = float(
        max(
            comparison_df["income"].max() if not comparison_df.empty else 0.0,
            comparison_df["expenses"].max() if not comparison_df.empty else 0.0,
        )
    )
    tick_vals, tick_text = _build_inr_yaxis_ticks(max_val)

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            name="Income",
            x=comparison_df["month_label"],
            y=comparison_df["income"],
            marker=dict(color=INCOME_COLOR, line=dict(width=0)),
            customdata=custom_income,
            hovertemplate="<b>Income:</b> %{customdata[1]}<extra></extra>",
        )
    )

    fig.add_trace(
        go.Bar(
            name="Expenses",
            x=comparison_df["month_label"],
            y=comparison_df["expenses"],
            marker=dict(color=EXPENSE_COLOR, line=dict(width=0)),
            customdata=custom_expense,
            hovertemplate=(
                "<b>Expenses:</b> %{customdata[1]}<br>"
                "<b>Monthly Savings:</b> %{customdata[2]}<extra></extra>"
            ),
        )
    )

    fig.update_layout(
        barmode="group",
        bargap=0.28,
        bargroupgap=0.12,
        height=390,
        margin=dict(l=16, r=16, t=24, b=24),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font=dict(
            family='-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif',
            color="#334155",
            size=13,
        ),
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor="#FFFFFF",
            bordercolor="#CBD5E1",
            font=dict(color="#0F172A", size=13),
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1.0,
            title_text="",
            font=dict(size=13, color="#334155"),
        ),
        xaxis=dict(
            title="",
            showgrid=False,
            linecolor="#E2E8F0",
            tickfont=dict(color="#475569", size=12),
        ),
        yaxis=dict(
            title="",
            tickmode="array",
            tickvals=tick_vals,
            ticktext=tick_text,
            gridcolor="#EDF2F7",
            zerolinecolor="#CBD5E1",
            tickfont=dict(color="#475569", size=12),
        ),
    )

    return fig


def render_comparison_section(snapshot: DashboardSnapshot) -> None:
    """Render the monthly Income vs. Expenses chart inside a clean card."""
    comparison_df = snapshot.monthly_comparison

    with st.container(border=True):
        st.markdown(
            """
            <p class="mm-section-title">Income vs. Expenses</p>
            <p class="mm-section-subtitle">Monthly comparison across all recorded periods (INR)</p>
            """,
            unsafe_allow_html=True,
        )

        if comparison_df.empty:
            st.markdown(
                '<p class="mm-empty-muted">No monthly transaction history is available to plot yet.</p>',
                unsafe_allow_html=True,
            )
            return

        fig = build_income_vs_expenses_chart(comparison_df)
        st.plotly_chart(
            fig,
            use_container_width=True,
            config={
                "displayModeBar": False,
                "responsive": True,
            },
        )


def _render_snapshot_rows(
    df: pd.DataFrame,
    name_col: str,
    value_col: str,
    value_color: str,
    empty_message: str,
) -> str:
    """Build clean HTML rows for latest savings accounts or loans."""
    if df.empty:
        return f'<p class="mm-empty-muted">{html.escape(empty_message)}</p>'

    rows_html: list[str] = []
    for _, row in df.iterrows():
        name = html.escape(str(row[name_col]))
        date_str = pd.Timestamp(row["date"]).strftime("%d %b %Y")
        amount_str = html.escape(format_inr(float(row[value_col])))
        rows_html.append(
            dedent(f"""
            <div class="mm-list-row">
                <div>
                    <div class="mm-list-name">{name}</div>
                    <div class="mm-list-date">As of {html.escape(date_str)}</div>
                </div>
                <div class="mm-list-amount" style="color: {value_color};">{amount_str}</div>
            </div>
            """)
        )
    return "".join(rows_html)


def render_balance_breakdowns(snapshot: DashboardSnapshot) -> None:
    """Render calm account and loan latest-snapshot cards beneath the chart."""
    savings_rows = _render_snapshot_rows(
        snapshot.latest_savings,
        name_col="account",
        value_col="balance",
        value_color="#1E5693",
        empty_message="No savings accounts recorded in data/savings.csv.",
    )
    debt_rows = _render_snapshot_rows(
        snapshot.latest_debts,
        name_col="loan",
        value_col="outstanding_balance",
        value_color="#A3443F",
        empty_message="No loans recorded in data/debts.csv.",
    )

    st.html(
        dedent(f"""
        <div class="mm-snapshot-grid">
            <div class="mm-section-card">
                <p class="mm-section-title">Savings Accounts</p>
                <p class="mm-section-subtitle">Latest recorded balance per account</p>
                {savings_rows}
            </div>
            <div class="mm-section-card">
                <p class="mm-section-title">Loans &amp; Debt</p>
                <p class="mm-section-subtitle">Latest recorded outstanding balance per loan</p>
                {debt_rows}
            </div>
        </div>
        """),
    )


def main() -> None:
    """Application entrypoint for the Money Manager Streamlit dashboard."""
    st.set_page_config(
        page_title="Money Manager",
        page_icon="₹",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    inject_styles()

    bundle = load_all_data(DATA_DIR)
    snapshot = build_dashboard_snapshot(
        transactions_df=bundle.transactions.df,
        savings_df=bundle.savings.df,
        debts_df=bundle.debts.df,
    )

    render_header(snapshot)
    render_freshness_and_notices(bundle, snapshot)
    render_summary_cards(snapshot)
    render_comparison_section(snapshot)
    render_balance_breakdowns(snapshot)


if __name__ == "__main__":
    main()
