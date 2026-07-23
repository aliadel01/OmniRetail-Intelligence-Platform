## Ingestion Layer

### Table of Contents
1. [Overview](#overview)
2. [Landing Strategy per File Format](#landing-strategy-per-file-format)
3. [Metadata Columns](#metadata-columns)
4. [Table Design Strategy by Archetype](#table-design-strategy-by-archetype)
    - [Archetype A — Static Reference Dimensions](#archetype-a--static-reference-dimensions-date-time-statustype-taxrate-industry-tradetype)
    - [Archetype B — Schema-Shifting CDC Facts](#archetype-b--schema-shifting-cdc-facts-account-customer-trade-holdinghistory-watchhistory-dailymarket)
    - [Archetype C — Full Re-Extract Snapshot](#archetype-c--full-re-extract-snapshot-prospect)
    - [Archetype D — Parsed Structural Sources](#archetype-d--parsed-structural-sources-customermgmtxml-finwire)
5. [Python Ingestion Scripts](#python-ingestion-scripts)

### Overview
Using Python scripts to implement the ingestion layer.

Our 21 sources are not homogeneous, so a single bronze pattern won't fit all of them. There are really **four distinct source archetypes** hiding in this data dictionary, and each needs a different bronze strategy:

| Archetype | Sources | Defining trait | Bronze implication |
| --- | --- | --- | --- |
| **A. Static/reference dimensions** | Date, Time, StatusType, TaxRate, Industry, TradeType | Loaded once (Batch1), never change again | Simple full-load, no dedup logic needed, no CDC handling |
| **B. Schema-shifting CDC facts** | Account, Customer, Trade, HoldingHistory, WatchHistory, DailyMarket | Column count differs between Batch1 and Batch2/3 | Bronze must absorb both shapes into one target schema; CDC columns must be defaulted (`_cdc_flag = 'I'`, `_cdc_dsn = 0`) for Batch1 rows |
| **C. Snapshot/full-refresh dimensions** | Prospect | No CDC, but re-extracted in full every batch | Bronze must not naively append without context — needs a batch-tagged full snapshot pattern |
| **D. Non-tabular / structural outliers** | CustomerMgmt.xml (nested XML), FINWIRE (fixed-width, 3 record types in one file), TradeHistory (Batch1-only, no incremental counterpart) | Require pre-parsing before they can even become "rows" | Bronze needs a flattening/parsing sub-stage before landing; can't be a pure 1:1 copy of the file |

Get this classification right first. Almost every downstream design decision (dbt source config, incremental strategy) is a function of which archetype a source belongs to — not of the source individually.

---

### Landing Strategy per File Format

| Format | Sources | Landing approach |
| --- | --- | --- |
| **Pipe-delimited flat file** | Account, Customer, Trade, HoldingHistory, WatchHistory, DailyMarket, CashTransaction, Date, Time, StatusType, TaxRate, Industry, TradeType, TradeHistory | Parse in Python, stage as normalized CSV, then execute bulk load via `COPY INTO` with `PUT` into an internal stage. One bronze table per file, column-for-column, plus metadata columns. |
| **Comma-delimited** | HR, Prospect | Same bulk `COPY INTO` strategy as above, using comma-delimited staging configuration. |
| **Fixed-width, multi-record-type** | FINWIRE | **Cannot land as one flat table.** Needs a pre-parse step that reads the 15-char PTS + 3-char RecType prefix and routes each line to one of three raw shapes (CMP/SEC/FIN) before insert. Do this parsing in Python — fixed-width substring parsing in SQL is fragile and unreadable. Land as three separate tables: `bronze_finwire_cmp`, `bronze_finwire_sec`, `bronze_finwire_fin`. |
| **Nested XML** | CustomerMgmt.xml | Needs flattening before it's tabular. Two children (Customer attributes, nested Account elements) means this is naturally two output tables: a customer-management-event table and a customer-account-link table, joined by `C_ID`/`ActionTS`. Do this flattening in Python using standard library (`xml.etree.ElementTree`). |
| **Control files (BatchDate.txt)** | BatchDate | Not a bronze data table at all — treat as ingestion metadata/config, read once per run to parameterize the batch ID and as-of date used to tag every other row landed in that run. |
| **Audit CSVs (`*_audit.csv`)** | Per component | Land into a **dedicated reconciliation table** (`bronze_source_audit`), separate from entity bronze tables. This becomes your row-count ground truth for QA. |

---

### Metadata Columns — Apply Uniformly, No Exceptions

Every bronze table, regardless of archetype, carries the same audit envelope:

* `_batch_id` — which batch (1, 2, 3, …) this row was loaded in. Useful for tracking and debugging.
* `_source_file` — literal filename, useful when a source spans multiple physical files (e.g., FINWIRE is quarterly: `FINWIRE2015Q4`, etc.).
* `_loaded_at` — ingestion timestamp (wall clock of the load, not business time).
* `_row_hash` — a hash of the business columns (SHA-256), used later for change detection and dedup logic without relying on CDC_FLAG alone (useful safety net for sources like CashTransaction where CDC presence is unconfirmed in your spec excerpt).

For CDC sources specifically, also standardize:

* `_cdc_flag` (normalized from `CDC_FLAG`, backfilled as `'I'` for Batch1).
* `_cdc_dsn` (normalized from `CDC_DSN`, backfilled as `0` for Batch1).

Keep these prefixed and consistent (`_batch_id`, not `batch_id`) so they're visually distinguishable from business columns in every model and never collide with a real column name.

---

### Table Design Strategy by Archetype

#### Archetype A — Static Reference Dimensions (Date, Time, StatusType, TaxRate, Industry, TradeType)

* **Ingestion behavior:** Plain append-only, loaded once during Batch1.
* **Optimization:** Table sizes are tiny (hundreds to low thousands of rows). No clustering or complex logic required.

#### Archetype B — Schema-Shifting CDC Facts (Account, Customer, Trade, HoldingHistory, WatchHistory, DailyMarket)

* **Ingestion behavior:** Plain append-only. All versions of rows across batches land as full history in bronze.
* **Batch isolation:** If a batch load fails, re-running is handled cleanly via standard SQL: `DELETE FROM bronze_table WHERE _batch_id = N;` followed by re-ingestion.
* **CDC handling:**
  * `_cdc_flag` and `_cdc_dsn` columns exist across all rows.
  * Batch1 backfills synthetic values (`_cdc_flag = 'I'`, `_cdc_dsn = 0`).
  * WatchHistory and DailyMarket are insert-only (`_cdc_flag = 'I'`).


* **Silver layer resolution:** Downstream queries/models resolve the "current state" using window functions:
```sql
QUALIFY ROW_NUMBER() OVER (PARTITION BY entity_id ORDER BY _cdc_dsn DESC) = 1

```



#### Archetype C — Full Re-Extract Snapshot (Prospect)

* **Design:** Each batch's full extract lands as its own generation, tagged by `_batch_id`. Bronze keeps every batch's full snapshot (don't overwrite) — storage is cheap, and point-in-time comparison of prospect lists across batches becomes trivial.
* **Silver layer resolution:** To query the latest state, downstream models simply filter by the latest batch:
```sql
WHERE _batch_id = (SELECT MAX(_batch_id) FROM bronze_prospect)

```



#### Archetype D — Parsed Structural Sources (CustomerMgmt.xml, FINWIRE)

* **Design:** Land as multiple bronze tables per the parsing done in Python (`bronze_finwire_cmp`, `_sec`, `_fin`; customer-event and customer-account-link tables for XML).
* **Ingestion behavior:** Plain append-only.
* **Polymorphic column resolution:** FINWIRE's `CoNameOrCIK` field is resolved at parse time into two explicit columns (`co_name`, `co_cik`, one of which is `NULL` per row) rather than carrying an ambiguous single column into bronze.

#### TradeHistory (Batch1-Only Fact)

* **Design:** Plain append-only table. It contains no incremental updates or CDC machinery. Loaded once during Batch1.

#### Audit Files (`*_audit.csv`)

* **Design:** Land into one unified `bronze_source_audit` table. This is your reconciliation source of truth — treat it as a first-class bronze table used by automated QA scripts to match ingested row counts against vendor totals.


Use this section at the end of the file:


### Python Ingestion Scripts

The ingestion layer is implemented as a small Python package under the `ingestion/` folder. The structure below separates configuration, shared utilities, Snowflake access, and format-specific loaders so each source can be handled independently.

#### Python ingestion script structure

```text
ingestion/
├── .env
├── common.py
├── config.py
├── main.py
├── requirements.txt
├── snowflake_client.py
├── ddl/
│   └── bronze_schema.sql
└── loaders/
    ├── audit_loader.py
    ├── delimited_loader.py
    ├── finwire_loader.py
    └── xml_loader.py
```

#### What each file means and its purpose

- `.env`
  - Stores local environment variables and secrets such as Snowflake credentials, batch parameters, and runtime settings.
  - This file is typically not committed to source control.

- `common.py`
  - Contains shared helper functions used across the ingestion package.
  - It usually includes logging, date handling, file utilities, validation, and reusable parsing helpers.

- `config.py`
  - Centralizes configuration loading and default values.
  - It reads settings from `.env` and exposes them to the rest of the package.

- `main.py`
  - This is the main entry point of the ingestion pipeline.
  - It orchestrates the workflow, decides which loaders to run, and controls the load process.

- `requirements.txt`
  - Lists the Python dependencies required by the ingestion scripts.
  - Used to install the environment for running the pipeline.

- `snowflake_client.py`
  - Wraps Snowflake connection and execution logic.
  - Its purpose is to abstract database operations such as connecting, executing SQL, and uploading staged files.

- `ddl/01_bronze_schema.sql`
  - Contains the SQL used to create the bronze schema and bronze tables.
  - This file ensures the landing tables exist before loading data.

- `loaders/audit_loader.py`
  - Handles audit CSV files such as `*_audit.csv`.
  - It loads reconciliation data into a dedicated bronze audit table for QA and row-count validation.

- `loaders/delimited_loader.py`
  - Handles pipe-delimited or other flat-file sources.
  - It parses the file, normalizes values, and prepares rows for bulk load into Snowflake.

- `loaders/finwire_loader.py`
  - Handles FINWIRE fixed-width data.
  - It parses the multi-record format and routes each row into the correct bronze table.

- `loaders/xml_loader.py`
  - Parses nested XML files such as `CustomerMgmt.xml`.
  - It flattens the XML structure into tabular bronze outputs.

#### How the scripts work together

1. `main.py` starts the ingestion process.
2. `config.py` and `.env` provide runtime settings.
3. The appropriate loader parses the source data into a normalized format.
4. `snowflake_client.py` loads the parsed data into Snowflake.
5. `ddl/01_bronze_schema.sql` ensures the target tables already exist.
6. Audit files are processed separately to support reconciliation and QA.