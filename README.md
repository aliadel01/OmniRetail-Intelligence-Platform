# Brokerage Data Platform

## Status: 🚧 In Progress — Phase 0 of 9

## What this is
A production-shaped data platform built on the TPC-DI benchmark, run in its
native brokerage domain (customers, accounts, trades, holdings, financial
newswire) on the Databricks Lakehouse — not reframed into another industry.
The **goal** is to demonstrate **real multi-source integration**, **data quality**
engineering, **batch + incremental/streaming** processing, and **warehouse** design
at meaningful scale.

## Why TPC-DI
TPC-DI is the only widely-used benchmark purpose-built to simulate real
data integration pain: **18 source files** across **5 independent systems**, in
**3 genuinely different formats** (CSV, XML, fixed-width-no-delimiter), with
documented real **data quality problems** (mixed record types, missing fields,
non-uniform updates) rather than synthetic mess injected after the fact.
It also scales to real "**big data**" volume (1GB → 2TB+ via scale factor) and
ships with an **incremental/streaming** variant. See ADR-001 for the full
comparison against TPC-DS and other alternatives considered.

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


## Data Sources
| ID | File Name | Format | Description / Purpose | Sample / Structure Example |
| :--- | :--- | :--- | :--- | :--- |
| **1** | `Date.txt` | Pipe-delimited (`\|`) | **Date dimension** — one row per calendar date, used across all fact tables for time-based joins. | `19680303\|1968-03-03\|Sunday\|1968\|1\|March\|3\|9\|1968Q1\|...` *(constructed to match documented fields: SK_DateID, DateValue, DayOfWeek, WeekNumber, etc.)* |
| **2** | `Time.txt` | Pipe-delimited (`\|`) | **Time-of-day dimension**, ordered by `SK_TimeID`; supports intraday trade timestamps. | `85\|01:23:45\|1\|"01"\|23\|"23"\|45\|"45"\|0\|0` — the time as text, e.g. `"01:23:45"`, is documented directly in the spec. |
| **3** | `StatusType.txt` | Pipe-delimited (`\|`) | **Reference/lookup table** for status codes used across Trade, Account, and other tables. | `ACTV\|Active` *(small static lookup table per spec)* |
| **4** | `TaxRate.txt` | Pipe-delimited (`\|`) | **Reference table** mapping tax rate codes to actual rates, used in trade/cash calculations. | `US1\|US - Federal Tax\|0.0500` *(matches documented purpose)* |
| **5** | `Industry.txt` | Pipe-delimited (`\|`) | **Reference table** of industry classification codes, feeds `DimCompany`. | `3721\|Aircraft\|1010` *(code, description, sector structure)* |
| **6** | `TradeType.txt` | Pipe-delimited (`\|`) | **Reference table** of trade type codes (buy, sell, short, cover, etc.). | `TMB\|Market-Buy\|0\|1` |
| **7** | `HR.csv` | CSV | **Employee master + reporting hierarchy**. Full-table extract each load — no CDC or incremental tracking. | `140501,2001-07-11,John,Smith,M,120 Main St,Chicago,IL,60601,US,140102,Managing Director` *(employee ID, hire date, name, address, manager ID, title)* |
| **8** | `Prospect.csv` | CSV | **Third-party marketing/prospect list** — names, contact info, demographic data. Some prospects are already customers. | `SMITHJ,John,,Smith,120 Main St,,Chicago,IL,60601,US,5551234567,,50000,M,1,750000,...` *(modeled as a full daily extract with no change indicators)* |
| **9** | `CustomerMgmt.xml` | XML (nested, hierarchical) | **New/updated customer + account actions** from CRM. A single record can describe a new account, account update, or customer-only update depending on *(structure matches Action/Customer/Account nesting)* | `<Action><Customer><Account>...</Account></Customer></Action>` |
| **10** | `FINWIRE` *(quarterly, e.g., `FINWIRE2015Q4`)* | Fixed-width (no delimiters) | **Financial newswire** — company (CMP), security (SEC), and financial (FIN) records mixed in one file, disambiguated by a `RecType` field at a fixed offset. | `20151230-163207CMPWWfcsOHprIDIUsPfRLrcLPlxaQ 0000004432ACTVMCA 1873092521088 Vessey Crescent M5D 1Z1 Winnipeg AL United States of AmericaMoreno...` *(PTS timestamp + RecType CMP + fixed-width fields)* |
| **11** | `Trade.txt` | Delimited text | **Core trade transaction fact** — one row per trade, links to account, security, trade type, and status. | `1500000,2015-03-03 09:12:00,CMPT,50,QCOM,25000.00,5000001,140501` *(T_ID, timestamp, status, quantity, symbol, price, account, employee)* |
| **12** | `TradeHistory.txt` | Delimited text | **Status-change history per trade** — tracks trade lifecycle (e.g., pending &rarr; submitted &rarr; completed) and corresponds to `T_ID`. | `1500000,2015-03-03 09:12:00,PNDG` *(trade ID + timestamp + status type)* |
| **13** | `HoldingHistory.txt` | Delimited text | **Snapshot of security holdings** resulting from trades — links a trade to its effect on a customer's position. | `1500000,1499998,QCOM,5000001,100` *(trade ID, prior holding trade ID, symbol, account, quantity)* |
| **14** | `CashTransaction.txt` | Delimited text | **Cash movement** resulting from a trade or account activity. | `5000001,2015-03-03 09:12:05,25000.00,"Cash from sale of QCOM"` *(account, timestamp, amount, description)* |
| **15** | `WatchHistory.txt` | Delimited text | **Customer watchlist additions/removals** — tracks which securities a customer is actively monitoring. | `1500000,QCOM,2015-03-03,ACTV` *(customer ID, symbol, date, action)* |
| **16** | `DailyMarket.txt` | Delimited text | **Daily security price/volume snapshot** — feeds market-data fact tables. | `2015-03-03,QCOM,68.42,68.90,67.85,4200000,1250000000` *(date, symbol, close, high, low, volume, market cap)* |
| **17** | `BatchDate.txt` | Plain text (single value) | **Control file** marking the "as-of" date for the current batch — used by the pipeline to identify the load phase. | `2015-03-03` |
| **18** | `*_audit.csv` *(one per component)* | CSV | **Auto-generated per-table row counts** and control totals — used to validate that a load completed correctly. | `TableName,RowCount HR,5000` *(first record contains headers)* |

Department classification
1. Human Resources (HR) 
    - `HR.csv` (7): Employee master list, salaries, and reporting structures.
2. Marketing & Client Relationship Management (CRM)
    - `Prospect.csv` (8): Third-party prospect list for marketing campaigns.
    - `CustomerMgmt.xml` (9): New and updated customer and account actions.
    - `WatchHistory.txt` (15): User behavior data (which stocks customers are actively watching on the app).
3. Brokerage & Trading Operations
    - `Trade.txt` (11): Core trade transaction fact table.
    - `TradeHistory.txt` (12): Status-change history per trade.
    - `HoldingHistory.txt` (13): Snapshot of security holdings resulting from trades.
    - `TradeType.txt` (6) & `StatusType.txt` (3): System lookup codes defining trade behaviors and execution states.
4. Finance, Treasury & Market Research
    - `CashTransaction.txt` (14): Cash movement resulting from trades or account activities.
    - `TaxRate.txt` (4): Tax jurisdictions applied to investment gains.
    - `DailyMarket.txt` (16): Daily security price and volume snapshot for market data.
    - `FINWIRE` (10): Financial newswire providing company, security, and financial records.
    - `Industry.txt` (5): Business sector categorizations used to classify companies.
5. IT, Data Platform & Audit (Enterprise Shared Services)
    - `Date.txt` (1) & `Time.txt` (2): Core date and time dimensions for fact table joins.
    - `BatchDate.txt` (17): Control file marking the "as-of" date for the current batch.
    - `*_audit.csv` (18): Auto-generated per-table row counts and control totals for load validation.

## How to Run This
[Not written yet — will document once Phase 2 is stable and repeatable.]

## Documentation
- Architecture Decision Records (`./docs/adr/`)
- Data Dictionary (`./docs/data-dictionary.md`)
- Data Quality Report (`./docs/dq-report.md`)
- Runbook (`./docs/runbook.md`)
- Case Study (`./docs/case-study.md`)
- Incident Notes (`./docs/incident-notes.md`)

## Honest Limitations
[To be filled in as the project progresses — e.g. streaming layer is
daily-batch via Augmented Incremental, not sub-second event streaming,
unless a Kafka layer is added on top and labeled as simulated.]

## Tech Stack