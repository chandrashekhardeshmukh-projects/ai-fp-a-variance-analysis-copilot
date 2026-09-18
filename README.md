# 📊 AI-Powered FP&A Variance Analysis Copilot

> An interactive FP&A analytics application designed to automate financial performance analysis, variance investigation, revenue driver decomposition, materiality screening, departmental drill-downs, and management commentary.

![Python](https://img.shields.io/badge/Python-3.x-blue)
![Streamlit](https://img.shields.io/badge/Framework-Streamlit-red)
![Pandas](https://img.shields.io/badge/Data-Pandas-150458)
![Plotly](https://img.shields.io/badge/Visualization-Plotly-3F4F75)
![FP&A](https://img.shields.io/badge/Domain-FP%26A-green)

---

## 🚀 Project Overview

The **AI-Powered FP&A Variance Analysis Copilot** is a finance analytics application built to simulate how an FP&A team can move from raw financial data to management-ready insights.

The application brings several recurring FP&A activities into a single analytical workflow:

**Financial Data → P&L Analysis → Variance Analysis → Driver Decomposition → Materiality Screening → Department Drill-down → Management Commentary → Interactive P&L Queries**

Instead of manually reviewing multiple spreadsheets and calculating individual variances, the application performs the calculations programmatically and presents the results through an interactive dashboard.

The project uses **illustrative/demo financial data** and is intended for educational and portfolio purposes.

---

# 🎯 Business Problem

FP&A teams regularly need to answer questions such as:

- How did actual revenue perform against budget?
- Why is EBITDA below or above plan?
- Which P&L lines are driving the variance?
- Is the revenue variance caused by price, volume, or product mix?
- Which departments are responsible for the largest deviations?
- Which variances are financially material?
- What are the largest favorable and unfavorable drivers?
- How should the financial results be communicated to management?

Traditional spreadsheet-based analysis can require repeated manual calculations, filtering, reconciliation, and preparation of management commentary.

This project demonstrates how those activities can be brought together into a single analytical application.

---

# 💡 Core Capabilities

## 1. Executive Performance Dashboard

Provides a high-level management view of financial performance.

Key metrics include:

- Total Revenue
- Gross Profit
- EBITDA
- EBITDA Margin
- Revenue vs Budget
- Revenue vs Forecast
- Revenue vs Prior Year
- Operating Cost vs Budget
- EBITDA variance bridge
- Departmental EBITDA comparison

The dashboard is designed to answer:

> **"What happened to overall financial performance?"**

---

# 📑 2. P&L Variance Analysis

The application generates a structured P&L comparison between:

- Budget
- Actual
- Variance
- Variance %
- Favorability

The analysis includes major financial line items such as:

- Gross Revenue
- Cost of Goods Sold
- Gross Profit
- Marketing Expense
- Employee Expense
- Technology Expense
- Other Operating Expenses
- EBITDA

### Variance calculation

For a standard financial metric:

```text
Variance = Actual - Budget
