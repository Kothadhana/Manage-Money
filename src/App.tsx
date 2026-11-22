/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

export default function App() {
  return (
    <main className="min-h-screen bg-[#F6F8FA] text-[#0F172A] px-6 py-12 font-sans">
      <div className="mx-auto max-w-2xl rounded-2xl border border-[#E5E9F0] bg-white p-8 shadow-sm">
        <div className="border-b border-[#E5E9F0] pb-5">
          <h1 className="text-2xl font-bold tracking-tight text-[#0F172A]">
            Money Manager — Version 1
          </h1>
          <p className="mt-1 text-sm text-[#526071]">
            Pure Python + Streamlit Personal Finance Dashboard
          </p>
        </div>

        <p className="mt-5 text-sm leading-relaxed text-[#334155]">
          This project has been generated strictly in <strong>Python</strong> using{' '}
          <strong>Streamlit</strong>, <strong>Pandas</strong>, <strong>Plotly</strong>, and{' '}
          <strong>Pytest</strong>, with all fictional financial data stored locally in{' '}
          <code className="rounded bg-[#F1F5F9] px-1.5 py-0.5 text-xs">data/</code> CSV files.
        </p>

        <div className="mt-6 rounded-xl border border-[#E5E9F0] bg-[#F8FAFC] p-5">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-[#64748B]">
            Run Locally
          </h2>
          <pre className="mt-3 overflow-x-auto text-xs leading-6 text-[#0F172A]">
{`pip install -r requirements.txt
streamlit run app.py
pytest`}
          </pre>
        </div>

        <div className="mt-6 rounded-xl border border-[#E5E9F0] bg-white p-5">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-[#64748B]">
            Project Files
          </h2>
          <ul className="mt-3 space-y-1.5 font-mono text-xs text-[#334155]">
            <li>app.py — Streamlit dashboard UI</li>
            <li>services/data_loader.py — CSV loading &amp; input validation</li>
            <li>services/finance.py — Financial calculations, freshness check &amp; INR formatting</li>
            <li>tests/test_finance.py — Pytest unit test suite</li>
            <li>data/transactions.csv, data/savings.csv, data/debts.csv — Sample datasets</li>
            <li>requirements.txt, pytest.ini, .streamlit/config.toml, README.md</li>
          </ul>
        </div>
      </div>
    </main>
  );
}
