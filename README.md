# Brokerage Data Platform

## Status: 🚧 In Progress — Phase 0 of 9

## What this is
A production-shaped data platform built on the TPC-DI benchmark, run in its
native brokerage domain (customers, accounts, trades, holdings, financial
newswire).
The **goal** is to demonstrate **real multi-source integration**, **data quality**
engineering, **batch** processing, and **warehouse** design
at meaningful scale.

## Why TPC-DI
TPC-DI is the only widely-used benchmark purpose-built to simulate real
data integration pain: **18 source files** across **5 independent systems** that these five systems know **nothing** about each other, in
**3 genuinely different formats** (CSV, XML, fixed-width-no-delimiter), with
documented real **data quality problems** rather than synthetic mess injected after the fact.
It also scales to real "**big data**" volume (1GB → 2TB+ via scale factor) and
ships with an **incremental/streaming** variant.

## Business Framing
This project stays in TPC-DI's native domain — a brokerage firm managing
customer accounts, trades, holdings, and market data. The operational story mirrors real
brokerage pain points:
- **Trade & settlement visibility** — can operations confirm a trade
  processed correctly across the trade, cash, and holding tables it
  touches, without manual reconciliation?
- **Customer & account trust** — CRM updates arrive as mixed record types
  (new account, updated account, customer-only update) in the same file;
  can the platform resolve these correctly and keep an auditable history?
- **Market & financial data reliability** — FINWIRE's commingled company,
  security, and financial records feed valuation and reporting; a parsing
  error here has direct downstream impact on numbers stakeholders trust.
- **Timely reporting** — moving from a single quarterly historical load
  toward genuine daily delivery (Augmented Incremental) reflects the real
  shift from batch-only reporting to near-real-time operational visibility.

## Architecture
![Architecture Diagram](./docs/architecture-diagram.png)

## Data Sources
This overview is a high-level summary of the source files, grouped by the five independent source systems (OLTP, HR DB, Prospect Vendor, Financial Newswire, and Customer Management) they originate from. For a full file-by-file dictionary, see [docs/datasources.md](./docs/datasources.md).

1. Customer Management System (Customer Mgmt)
    - `CustomerMgmt.xml`: Historical snapshot of new and updated customer and account creations.
    - `Customer.txt` (Incremental): Pipeline delta updates for customer profiles (replaces the XML in subsequent batches).
    - `Account.txt` (Incremental): Pipeline delta updates for trading accounts (replaces the XML in subsequent batches).
2. Human Resources Database (HR DB)
    - `HR.csv`: Employee master list, internal organization hierarchy, and salaries.
3. Third-Party Marketing Vendor (Prospect List)
    - `Prospect.csv`: Re-delivered complete prospect lists used to identify and target high-value potential clients.
4. Financial Newswire (Market Feed)
    - `FINWIRE`: Semi-structured fixed-width records containing historical corporate directory listings, security specifications, and financial statements.
    - `DailyMarket.txt`: Daily security market price snapshots (opening, high, low, close) and trading volumes.
    - `Industry.txt`: Standard sector definitions used to categorize companies.
5. On-Line Transaction Processing System (OLTP DB)
    - `Trade.txt`: Core transactional records representing historical and incremental stock trades.
    - `TradeHistory.txt`: Full state-transition log tracking trades from submission to completion.
    - `HoldingHistory.txt`: Incremental modifications of security share quantities held in user portfolios.
    - `CashTransaction.txt`: Register of all deposit, withdrawal, and transaction-related cash adjustments.
    - `WatchHistory.txt`: User behavior logs containing security watchlist additions and removals.
    - `TradeType.txt` & `StatusType.txt`: System configuration lookup codes defining trading behaviors and transaction execution states.
    - `TaxRate.txt`: Government tax rates applied to investment gains.
    - `Date.txt` & `Time.txt`: Master temporal dimensions used to structure and time-stamp transactions.
    - `BatchDate.txt`: System control metadata marking the active processing date boundary for incoming data.
    - `*_audit.csv`: Automatically generated check totals used to validate ingestion pipelines against data loss.

## How to Run This
[Not written yet — will document once Phase 2 is stable and repeatable.]

## Documentation
- Architecture Decision Records (`./docs/adr/`)
- Data Dictionary (`./docs/data-dictionary.md`)
- Data Quality Report (`./docs/dq-report.md`)
- Runbook (`./docs/runbook.md`)
- Case Study (`./docs/case-study.md`)
- Incident Notes (`./docs/incident-notes.md`)

## Tech Stack