"""
CLI entry point for bronze-layer ingestion into Snowflake.

Expected directory layout:

    <data-dir>/
        batch1/
            Date.txt
            Time.txt
            StatusType.txt
            TaxRate.txt
            Industry.txt
            TradeType.txt
            HR.csv
            Prospect.csv
            CustomerMgmt.xml
            FINWIRE2015Q4          (one or more FINWIRE* files)
            Trade.txt
            TradeHistory.txt
            HoldingHistory.txt
            WatchHistory.txt
            DailyMarket.txt
            CashTransaction.txt
            BatchDate.txt
            *_audit.csv
        batch2/
            Account.txt
            Customer.txt
            Prospect.csv
            Trade.txt
            HoldingHistory.txt
            WatchHistory.txt
            DailyMarket.txt
            CashTransaction.txt
            BatchDate.txt
            *_audit.csv
        batch3/
            ...

A source that isn't present in a given batch directory is simply skipped —
scope per batch is driven entirely by file presence, so this script doesn't
need to know your batch scope matrix; the data directory expresses it.

Every loader normalizes its source into a local staging CSV, then PUTs it
to the Snowflake internal stage `ingest_stage` and COPY INTOs the target
table (see ADR-007). Staging files are written to a temp directory that is
cleaned up at the end of each run.

Usage:
    python -m ingestion.main --data-dir /path/to/data --batch-id 1 \\
        --account myorg-myaccount --user INGEST_USER --password '***' \\
        --role INGEST_ROLE --warehouse INGEST_WH \\
        --database brokerage_dwh --schema bronze

Run once per batch, in order (1, then 2, then 3, ...) — _cdc_dsn versioning
assumes monotonically increasing sequence numbers across batches.
"""
import argparse
import shutil
import tempfile
from pathlib import Path
from os import getenv
from dotenv import load_dotenv

from .config import DELIMITED_SOURCES
from .snowflake_client import get_connection
from .loaders.delimited_loader import load_delimited_source
from .loaders.finwire_loader import load_finwire_source
from .loaders.xml_loader import load_customer_mgmt_xml
from .loaders.audit_loader import load_audit_source, load_batch_date

load_dotenv()

def run_batch(conn, data_dir: Path, batch_id: int, tmp_dir: Path) -> dict:
    """Execute bronze-layer data ingestion for a single batch directory.

    Processes all available source files (delimited text, XML, FINWIRE, and audit CSVs)
    within a specific batch folder and loads them into their corresponding 
    bronze-layer Snowflake tables.

    The execution order follows a strict sequence:
        1. Control File (`BatchDate.txt`): Loaded first to set the batch context.
        2. Delimited Sources: Iterates over configured files in `DELIMITED_SOURCES`.
        3. XML Sources: Parses `CustomerMgmt.xml` if present.
        4. FINWIRE Files: Dynamically detects and loads `FINWIRE*` flat files.
        5. Audit Files: Loads any `*_audit.csv` reconciliation files.

    Note:
        Files that are not present in the batch directory are gracefully skipped 
        without throwing errors, allowing dynamic batch scoping.

    Args:
        conn (snowflake.connector.SnowflakeConnection): Active Snowflake connection object.
        data_dir (Path): Path to the root data directory containing `batchX` subfolders.
        batch_id (int): The numeric ID of the batch to process (e.g., 1, 2, 3).
        tmp_dir (Path): Path to a temporary directory used for local CSV staging.

    Returns:
        dict: A dictionary mapping source/file names to the total count of 
              ingested rows. Example:
              {
                  "Trade": 15000,
                  "customer_mgmt_xml": 450,
                  "FINWIRE2015Q4": 3200,
                  "Trade_audit.csv": 12
              }

    Raises:
        FileNotFoundError: If the target batch directory (`batch<batch_id>`) 
                           does not exist inside `data_dir`.
    """    
    batch_dir = data_dir / f"Batch{batch_id}"
    if not batch_dir.exists():
        raise FileNotFoundError(f"No directory found for batch {batch_id}: {batch_dir}")

    summary = {}

    # Control file first — records the as-of date for this batch.
    batch_date_path = batch_dir / "BatchDate.txt"
    if batch_date_path.exists():
        load_batch_date(conn, batch_date_path, batch_id, tmp_dir)
        print(f"[batch {batch_id}] BatchDate.txt -> bronze_batch_control")

    # # All delimited sources present in this batch directory.
    for source_name, config in DELIMITED_SOURCES.items():
        filepath = batch_dir / config["filename"]
        if not filepath.exists():
            continue
        count = load_delimited_source(conn, config, filepath, batch_id, tmp_dir)
        summary[source_name] = count
        print(f"[batch {batch_id}] {source_name}: {count} rows -> {config['target_table']}")

    # XML source.
    xml_path = batch_dir / "CustomerMgmt.xml"
    if xml_path.exists():
        n_events, n_accounts = load_customer_mgmt_xml(conn, xml_path, batch_id, tmp_dir)
        summary["customer_mgmt_xml"] = n_events + n_accounts
        print(f"[batch {batch_id}] CustomerMgmt.xml: {n_events} events, {n_accounts} account links")
        
    # FINWIRE — quarterly files, filename pattern FINWIRE<year><quarter>.
    finwire_files = [
    f for f in batch_dir.glob("FINWIRE*") 
    if not f.name.endswith("_audit.csv")
    ]
    
    for finwire_path in sorted(finwire_files):
        n = load_finwire_source(conn, finwire_path, batch_id, tmp_dir)
        summary[finwire_path.name] = n
        print(f"[batch {batch_id}] {finwire_path.name}: {n} rows across CMP/SEC/FIN")

    # Audit reconciliation files.
    for audit_path in sorted(batch_dir.glob("*_audit.csv")):
        n = load_audit_source(conn, audit_path, batch_id, tmp_dir)
        summary[audit_path.name] = n
        print(f"[batch {batch_id}] {audit_path.name}: {n} rows -> bronze_source_audit")

    return summary


def main():
    parser = argparse.ArgumentParser(description="Bronze layer ingestion for brokerage-data-platform (Snowflake)")

    # Read default values from environment variables or override via CLI flags
    parser.add_argument("--data-dir", default=getenv("DATA_DIR"), help="Root directory containing batch1/, batch2/, ... subfolders")
    parser.add_argument("--batch-id", required=True, type=int, help="Batch number to ingest (e.g., 1, 2, 3)")
    parser.add_argument("--account", default=getenv("SNOWFLAKE_ACCOUNT"), help="Snowflake account identifier")
    parser.add_argument("--user", default=getenv("SNOWFLAKE_USER"), help="Snowflake user name")
    parser.add_argument("--password", default=getenv("SNOWFLAKE_PASSWORD"), help="Snowflake password")
    parser.add_argument("--role", default=getenv("SNOWFLAKE_ROLE"), help="Snowflake role")
    parser.add_argument("--warehouse", default=getenv("SNOWFLAKE_WAREHOUSE"), help="Snowflake warehouse")
    parser.add_argument("--database", default=getenv("SNOWFLAKE_DATABASE", "brokerage_dwh"), help="Snowflake database name")
    parser.add_argument("--schema", default=getenv("SNOWFLAKE_SCHEMA", "bronze"), help="Snowflake schema name")

    args = parser.parse_args()

    # Validate required parameters from .env or CLI flags
    required_configs = {
        "DATA_DIR": args.data_dir,
        "SNOWFLAKE_ACCOUNT": args.account,
        "SNOWFLAKE_USER": args.user,
        "SNOWFLAKE_PASSWORD": args.password,
        "SNOWFLAKE_ROLE": args.role,
        "SNOWFLAKE_WAREHOUSE": args.warehouse,
    }

    missing_keys = [key for key, val in required_configs.items() if not val]
    if missing_keys:
        parser.error(f"Missing configuration for: {', '.join(missing_keys)}. Please set them in your .env file or pass them via CLI flags.")

    conn = get_connection(args)
    data_dir = Path(args.data_dir)
    tmp_dir = Path(tempfile.mkdtemp(prefix=f"bronze_ingest_batch{args.batch_id}_"))

    try:
        summary = run_batch(conn, data_dir, args.batch_id, tmp_dir)
        total = sum(v for v in summary.values() if isinstance(v, int))
        print(f"\nBatch {args.batch_id} complete. Total rows ingested: {total}")
    finally:
        conn.close()
        shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()