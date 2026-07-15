# Source Data Dictionary — Incremental Batches (Batch2, Batch3)

## brokerage-data-platform

This covers only the **incremental** batches. Batch1 (historical load) has its
own separate dictionary — reference tables (Date, Time, StatusType, TaxRate,
Industry, TradeType), HR, FINWIRE, and `CustomerMgmt.xml` are loaded **once**
in Batch1 and are **not repeated here**.

| Batch | Represents | As-of Date |
|---|---|---|
| Batch2 | Incremental Update 1 | **2017-07-08** |
| Batch3 | Incremental Update 2 | **2017-07-09** |

Confirmed directly from the TPC-DI specification: Batch2 contains all files
used for Incremental Update 1, and Batch3 contains all files used for
Incremental Update 2 — these are the two post-historical daily deltas, not a
second full load.


## The Structural Shift From Batch1 → Batch2/Batch3

The **file format itself changes** between the historical and incremental
loads, not just the row count.

- **Batch1**: customer/account data arrives as **`CustomerMgmt.xml`** — nested
  XML, with `ActionType` (NEW/UPDACCT/UPDCUST/INACT/CLOSEACCT) determining the
  record shape.
- **Batch2 / Batch3**: customer/account data arrives as **flat, pipe-delimited
  `Account.txt` and `Customer.txt`** files — no XML, no ActionType. Instead,
  every incremental file carries two CDC control columns at the start of each
  row:

| Column | Meaning |
|---|---|
| `CDC_FLAG` | `I` = Insert (new record), `U` = Update (existing record changed) |
| `CDC_DSN` | Data Sequence Number — a monotonically increasing sequence identifying the order changes occurred, used to apply updates in the correct order |

This is a real, verified pattern (confirmed from an actual processed sample,
not constructed) — every incremental file in Batch2/Batch3 follows this same
`CDC_FLAG | CDC_DSN | ...` shape, which is the actual mechanism by which TPC-DI
simulates true CDC (Change Data Capture) from the source OLTP system.


## File-by-File Dictionary

### 1. Account.txt
**Format:** Pipe-delimited (`|`)  
**Scope:** Incremental (Batch 2 / Batch 3)  
**Target:** Feeds `DimAccount` (SCD2). Replaces the Account portion of Batch 1's XML.

| Column | Type | Description |
|---|---|---|
| CDC_FLAG | string | Action code (`I` = Insert, `U` = Update) |
| CDC_DSN | int | Change Data Capture Sequence Number |
| CA_ID | int | Unique Account ID |
| CA_B_ID | int | Managing Broker ID |
| CA_C_ID | int | Owner Customer ID |
| CA_NAME | string | Account description/name |
| CA_TAX_ST | int | Account tax status code (`0`, `1`, or `2`) |
| CA_ST_ID | string | Status code (`ACTV`, `INAC`) |

**Row Example:**  
`I|8214563|20469|1284|10284|WSrAJPnvZzbENxGPc...|0|ACTV`

---

### 2. Customer.txt
**Format:** Pipe-delimited (`|`)  
**Scope:** Incremental (Batch 2 / Batch 3)  
**Target:** Feeds `DimCustomer` (SCD2). Replaces the Customer portion of Batch 1's XML.

| Column | Type | Description |
|---|---|---|
| CDC_FLAG | string | Action code (`I` = Insert, `U` = Update) |
| CDC_DSN | int | Change Data Capture Sequence Number |
| C_ID | int | Customer ID |
| C_TAX_ID | string | Government Tax ID |
| C_GNDR | string | Gender code |
| C_TIER | int | Customer tier rating |
| C_DOB | date | Birth date |
| C_L_NAME | string | Last name |
| C_F_NAME | string | First name |
| C_M_NAME | string | Middle name |
| C_ADLINE1 | string | Address line 1 |
| C_ADLINE2 | string | Address line 2 |
| C_ZIPCODE | string | Zip code |
| C_CITY | string | City |
| C_STATE_PROV | string | State or Province |
| C_CTRY | string | Country |
| C_PRIM_EMAIL | string | Primary email address |
| C_ALT_EMAIL | string | Alternative email address |
| C_PHONE_1 | string | Primary phone number |
| C_PHONE_2 | string | Secondary phone number |
| C_PHONE_3 | string | Tertiary phone number |
| C_LCL_TX_ID | string | Local tax rate jurisdiction code |
| C_NAT_TX_ID | string | National tax rate jurisdiction code |

**Row Example:**  
`U|8214601|11078||||||||||||||Robin.M.Namiki@enigmail.net|||||`

---

### 3. CashTransaction.txt
**Format:** Pipe-delimited (`|`)  
**Scope:** Historical (Batch 1) & Incremental (Batch 2 / Batch 3)  
**Target:** Feeds `FactCashBalances` / `DimAccount` cash events.

| Column | Type | Description |
|---|---|---|
| CT_CA_ID | int | Unique Account ID |
| CT_DTS | timestamp | Execution date and time |
| CT_AMT | float | Cash movement amount (negative denotes withdrawals) |
| CT_NAME | string | Transaction description text |

**Row Example:**  
`I|4937695|6507|2017-07-08 10:16:09|5519.45|AYJRCJpzLBMJUWKjS...`

---

### 4. Trade.txt
**Format:** Pipe-delimited (`|`)  
**Scope:** Historical (Batch 1) & Incremental (Batch 2 / Batch 3)  
**Target:** Feeds `FactHoldings` and `FactTrades`.

| Column | Type | Description |
|---|---|---|
| T_ID | int | Unique Trade ID |
| T_DTStimestamp | timestamp | Trade execution timestamp |
| T_ST_ID | string | Transaction status (`CMPT`, `PNDG`, `CNCL`, `SBMT`) |
| T_TT_ID | string | Type of trade (`TMB`, `TMS`, `TSL`, `TLS`, `TLB`) |
| T_IS_CASH | int | Cash flag indicator (`0` or `1`) |
| T_S_SYMB | string | Unique Security Symbol |
| T_QTY | int | Share volume traded |
| T_BID_PRICE | float | Limit bid price requested |
| T_CA_ID | int | Executing Account ID |
| T_EXEC_NAME | string | Broker or trader name executing the trade |
| T_TRADE_PR | float | Realized market settlement price |
| T_CHRG | float | Transaction fee charged to account |
| T_COMM | float | Commission fee paid |
| T_TAX | float | Calculated tax fee applied to transaction |

**Row Example:**  
`0|2012-07-07 00:02:34|CMPT|TMB|0|AAAAAAAAAAAACQP|2939|9.57|0|3160|10.02|58.95|27.31|1611.19`

---

### 5. TradeHistory.txt
**Format:** Pipe-delimited (`|`)  
**Scope:** Historical (Batch 1 only)  
**Target:** Tracks step-by-step transaction lifecycle states.

| Column | Type | Description |
|---|---|---|
| TH_T_ID | int | Trade ID |
| TH_DTStimestamp | timestamp | Status update timestamp |
| TH_ST_ID | string | Status assigned at this timestamp (`ACTV`, `CMPT`, `PNDG`, `CNCL`, `SBMT`) |

**Row Example:**  
`0|2012-07-07 00:01:13|SBMT`

---

### 6. HoldingHistory.txt
**Format:** Pipe-delimited (`|`)  
**Scope:** Historical (Batch 1) & Incremental (Batch 2 / Batch 3)  
**Target:** Tracking security holdings snapshots over time.

| Column | Type | Description |
|---|---|---|
| HH_T_ID | int | Current Trade ID creating this holding change |
| HH_H_T_ID | int | Parent Trade ID originally purchasing the security holding |
| HH_BEFORE_QTY | int | Security volume held before current transaction execution |
| HH_AFTER_QTY | int | Security volume held after current transaction execution |

**Row Example:**  
`0|0|2939|1110`

---

### 7. DailyMarket.txt
**Format:** Pipe-delimited (`|`)  
**Scope:** Historical (Batch 1) & Incremental (Batch 2 / Batch 3)  
**Target:** Feeds `FactMarket` security price tracking.

| Column | Type | Description |
|---|---|---|
| DM_DATE | date | Market trading date (`YYYY-MM-DD`) |
| DM_S_SYMB | string | Security symbol ID |
| DM_CLOSE | float | Closing price at end of day trading |
| DM_HIGH | float | Peak price reached during daily trading session |
| DM_LOW | float | Minimum price dropped to during daily trading session |
| DM_VOL | int | Total volume traded during the day |

**Row Example:**  
`2015-07-06|AAAAAAAAAAAABOY|242.93|284.42|185.08|111904727`

---

### 8. WatchHistory.txt
**Format:** Pipe-delimited (`|`)  
**Scope:** Historical (Batch 1) & Incremental (Batch 2 / Batch 3)  
**Target:** Track customer watchlist events (additions and removals).

| Column | Type | Description |
|---|---|---|
| W_C_ID | int | Unique Customer ID owning the watchlist |
| W_S_SYMB | string | Target security symbol watched |
| W_DTStimestamp | timestamp | Action date and time |
| W_ACTION | string | Watch action (`ACTV` = Add/Active, `CNCL` = Delete/Cancel) |

**Row Example:**  
`17|AAAAAAAAAAAAAJR|2012-07-07 00:03:44|ACTV`

---

### 9. Prospect.csv
**Format:** CSV (comma-delimited `,`)  
**Scope:** Historical & Incremental (full-file dump delivered with every batch)  
**Target:** Marketing targets mapping to `DimProspect`.

| Column | Type | Description |
|---|---|---|
| AgencyID | string | Unique agency assigned tracking code |
| LastName | string | Prospect last name |
| FirstName | string | Prospect first name |
| MiddleInitial | string | Prospect middle initial |
| Gender | string | Gender (`M`, `F`, `U`) |
| AddressLine1 | string | Street address line 1 |
| AddressLine2 | string | Street address line 2 |
| PostalCode | string | Mailing Postal Code |
| City | string | Target City |
| State | string | State or Province |
| Country | string | Country name |
| Phone | string | Prospect contact number |
| Income | int | Annual income estimation |
| NumberCars | int | Registered household vehicles |
| NumberChildren | int | Estimated child count |
| MaritalStatus | string | Marital code (`S`, `M`, `D`, `W`) |
| Age | int | Estimated age |
| CreditRating | int | Financial credit rating code |
| OwnHome | string | House ownership flag (`O` = Owner, `R` = Renter) |
| Employer | string | Current employer name |
| CreditCard | string | Credit card brand held |
| NetWorth | int | Net worth calculation |

**Row Example:**  
`PEL0,PELLAND,Netti,,f,21847 olympia street,,T6b 1i1,Fairbanks,MA,United States of America,1-712-522-6088,368776,,3,W,20,760,O,Brink's,,1058868`

---

### 10. HR.csv
**Format:** CSV (comma-delimited `,`)  
**Scope:** Historical (Batch 1 only)  
**Target:** Employee master tracking dimension.

| Column | Type | Description |
|---|---|---|
| EmployeeID | int | Unique internal employee identifier |
| ManagerID | int | Manager's Employee ID |
| FirstName | string | Employee first name |
| LastName | string | Employee last name |
| DepartmentID | int | Department allocation code |
| OfficeCode | string | Location code |
| Phone | string | Work phone number |

**Row Example:**  
`1,3,Douglas,Ozkan,46,OFFICE7152,(726) 088-3331`

---

### 11. FINWIRE Files
**Format:** Plain text, fixed-width characters  
**Scope:** Historical (Batch 1 only)  
**Target:** Financial newswire tracking companies, securities, and financial records.

Records are parsed by character positions and branched by record type.

#### Company Record (`CMP`)
| Field | Positions | Width | Type | Description |
|---|---:|---:|---|---|
| PTS | 0-15 | 15 | string | Point-in-time timestamp |
| RecType | 15-18 | 3 | string | Record type identifier (`CMP`) |
| CompanyName | 18-78 | 60 | string | Legal company name |
| CIK | 78-88 | 10 | string | SEC Central Index Key |

---

### 12. Reference Dimensions
**Scope:** Historical batch-only helper files  
**Format:** Pipe-delimited (`|`) with no header rows

#### A. Industry.txt
| Column Index | Type | Example | Description |
|---|---|---|---|
| 0 | string | AASector | Industry abbreviation |
| 1 | string | Misc. Capital Goods | Full industry description |
| 2 | string | FNB | Broad market segment category |

#### B. StatusType.txt
| Column Index | Type | Example | Description |
|---|---|---|---|
| 0 | string | ACTV | Unique status code |
| 1 | string | Active | Status label |

#### C. TradeType.txt
| Column Index | Type | Example | Is Sell? | Is Market? |
|---|---|---|---|---|
| 0 | string | TMB | 0 | 1 |
| 1 | string | Market Buy | 0 | 1 |

#### D. TaxRate.txt
| Column Index | Type | Example | Description |
|---|---|---|---|
| 0 | string | US1 | Unique tax code |
| 1 | string | U.S. Income Tax Bracket for the poor | Description |
| 2 | float | 0.15 | Percentage rate |

#### E. Date.txt
**Columns:** 18  
Includes calendar attributes such as Date ID, Date string, month name, quarters, calendar year, week of year, day of week.

#### F. Time.txt
**Columns:** 10  
Includes time attributes such as Time ID, hour, minute, second, AM/PM indicators.

#### G. BatchDate.txt
**Format:** Plain text, 1 column, 1 row  
**Meaning:** Control file containing exactly one date value defining the batch load date.

---

### 13. Audit Control Files (`*_audit.csv`)
**Format:** CSV (comma-delimited `,`)  
**Scope:** Generated per file/batch  
**Target:** Control totals for data validation pipelines.

| Column | Type | Description |
|---|---|---|
| BatchID | int | Target Batch execution ID |
| FileName | string | File name reference being validated |
| MetricName | string | Validation target (e.g., `ROW_COUNT`) |
| Value | int | Numeric check value |


---

## Why This Matters For Your Pipeline

The CDC_FLAG/CDC_DSN pattern is the actual mechanism your ingestion logic
needs to branch on:
- `CDC_FLAG = 'I'` → new row, insert into Silver
- `CDC_FLAG = 'U'` → existing row changed, needs an SCD2 update (close out the
  old "current" row, insert a new one) — and because updates can be partial
  (as seen in the real Customer.txt sample above), your merge logic must
  carry forward unchanged fields rather than overwriting them with nulls

This is a materially different ingestion problem than Batch1's XML parsing,
and worth calling out explicitly in your ADRs — you are not just "loading
more of the same files," you are handling a genuinely different data
contract between the historical and incremental phases, which mirrors a
very real production pattern of full-load-then-CDC.