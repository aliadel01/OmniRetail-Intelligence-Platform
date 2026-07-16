from pathlib import Path
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Union
import pandas as pd

###############################################################################
# 1. CONFIGURATION & GLOBAL STATE
###############################################################################

ROOT = Path(r"data/")  # <-- Change this to your local path

# Global trackers for run summary
passed: List[str] = []
failed: List[str] = []


###############################################################################
# 2. FILE SCHEMAS
###############################################################################

SCHEMAS: Dict[str, List[str]] = {
    # BatchDate
    "BatchDate.txt": ["BATCH_DATE"],
    # Account (Incremental only)
    "Account.txt": [
        "CDC_FLAG",
        "CDC_DSN",
        "CA_ID",
        "CA_B_ID",
        "CA_C_ID",
        "CA_NAME",
        "CA_TAX_ST",
        "CA_ST_ID",
    ],
    # Customer (Incremental only)
    "Customer.txt": [
    "CDC_FLAG",
    "CDC_DSN",
    "C_ID",
    "C_TAX_ID",
    "C_ST_ID",
    "C_L_NAME",
    "C_F_NAME",
    "C_M_NAME",
    "C_GNDR",
    "C_TIER",
    "C_DOB",
    "C_ADLINE1",
    "C_ADLINE2",
    "C_ZIPCODE",
    "C_CITY",
    "C_STATE_PROV",
    "C_CTRY",
    "C_CTRY_1",
    "C_AREA_1",
    "C_LOCAL_1",
    "C_EXT_1",
    "C_CTRY_2",
    "C_AREA_2",
    "C_LOCAL_2",
    "C_EXT_2",
    "C_CTRY_3",
    "C_AREA_3",
    "C_LOCAL_3",
    "C_EXT_3",
    "C_PRIM_EMAIL",
    "C_ALT_EMAIL",
    "C_LCL_TX_ID",
    "C_NAT_TX_ID",
    ],
    "Customer.txt": [
    "CDC_FLAG",
    "CDC_DSN",
    "C_ID",
    "C_TAX_ID",
    "C_ST_ID",
    "C_L_NAME",
    "C_F_NAME",
    "C_M_NAME",
    "C_GNDR",
    "C_TIER",
    "C_DOB",
    "C_ADLINE1",
    "C_ADLINE2",
    "C_ZIPCODE",
    "C_CITY",
    "C_STATE_PROV",
    "C_CTRY",
    "C_CTRY_1",
    "C_AREA_1",
    "C_LOCAL_1",
    "C_EXT_1",
    "C_CTRY_2",
    "C_AREA_2",
    "C_LOCAL_2",
    "C_EXT_2",
    "C_CTRY_3",
    "C_AREA_3",
    "C_LOCAL_3",
    "C_EXT_3",
    "C_PRIM_EMAIL",
    "C_ALT_EMAIL",
    "C_LCL_TX_ID",
    "C_NAT_TX_ID",
    ],
    # HR
    "HR.csv": [
        "EmployeeID",
        "ManagerID",
        "EmployeeFirstName",
        "EmployeeLastName",
        "EmployeeMI",
        "EmployeeJobCode",
        "EmployeeBranch",
        "EmployeeOffice",
        "EmployeePhone",
    ],
    # Prospect
    "Prospect.csv": [
        "AgencyID",
        "LastName",
        "FirstName",
        "MiddleInitial",
        "Gender",
        "AddressLine1",
        "AddressLine2",
        "PostalCode",
        "City",
        "State",
        "Country",
        "Phone",
        "Income",
        "NumberCars",
        "NumberChildren",
        "MaritalStatus",
        "Age",
        "CreditRating",
        "OwnOrRentFlag",
        "Employer",
        "NumberCreditCards",
        "NetWorth",
    ],
    # Industry
    "Industry.txt": ["IN_ID", "IN_NAME", "IN_SC_ID"],
    # StatusType
    "StatusType.txt": ["ST_ID", "ST_NAME"],
    # TaxRate
    "TaxRate.txt": ["TX_ID", "TX_NAME", "TX_RATE"],
    # TradeType
    "TradeType.txt": ["TT_ID", "TT_NAME", "TT_IS_SELL", "TT_IS_MRKT"],
    # Time
    "Time.txt": [
        "SK_TimeID",
        "TimeValue",
        "HourID",
        "HourDesc",
        "MinuteID",
        "MinuteDesc",
        "SecondID",
        "SecondDesc",
        "MarketHoursFlag",
        "OfficeHoursFlag",
    ],
    # Date
    "Date.txt": [
        "SK_DateID",
        "DateValue",
        "DateDesc",
        "CalendarYearID",
        "CalendarYearDesc",
        "CalendarQtrID",
        "CalendarQtrDesc",
        "CalendarMonthID",
        "CalendarMonthDesc",
        "CalendarWeekID",
        "CalendarWeekDesc",
        "DayOfWeekNum",
        "DayOfWeekDesc",
        "FiscalYearID",
        "FiscalYearDesc",
        "FiscalQtrID",
        "FiscalQtrDesc",
        "HolidayFlag",
    ],
    # Trade History
    "TradeHistory.txt": ["TH_T_ID", "TH_DTS", "TH_ST_ID"],
    # Trade
    "Trade_Batch1": [
        "T_ID",
        "T_DTS",
        "T_ST_ID",
        "T_TT_ID",
        "T_IS_CASH",
        "T_S_SYMB",
        "T_QTY",
        "T_BID_PRICE",
        "T_CA_ID",
        "T_EXEC_NAME",
        "T_TRADE_PRICE",
        "T_CHRG",
        "T_COMM",
        "T_TAX",
    ],
    "Trade_Incremental": [
        "CDC_FLAG",
        "CDC_DSN",
        "T_ID",
        "T_DTS",
        "T_ST_ID",
        "T_TT_ID",
        "T_IS_CASH",
        "T_S_SYMB",
        "T_QTY",
        "T_BID_PRICE",
        "T_CA_ID",
        "T_EXEC_NAME",
        "T_TRADE_PRICE",
        "T_CHRG",
        "T_COMM",
        "T_TAX",
    ],
    # HoldingHistory
    "HoldingHistory_Batch1": [
        "HH_H_T_ID",
        "HH_T_ID",
        "HH_BEFORE_QTY",
        "HH_AFTER_QTY",
    ],
    "HoldingHistory_Incremental": [
        "CDC_FLAG",
        "CDC_DSN",
        "HH_H_T_ID",
        "HH_T_ID",
        "HH_BEFORE_QTY",
        "HH_AFTER_QTY",
    ],
    # WatchHistory
    "WatchHistory_Batch1": ["W_C_ID", "W_S_SYMB", "W_DTS", "W_ACTION"],
    "WatchHistory_Incremental": [
        "CDC_FLAG",
        "CDC_DSN",
        "W_C_ID",
        "W_S_SYMB",
        "W_DTS",
        "W_ACTION",
    ],
    # DailyMarket
    "DailyMarket_Batch1": [
        "DM_DATE",
        "DM_S_SYMB",
        "DM_CLOSE",
        "DM_HIGH",
        "DM_LOW",
        "DM_VOL",
    ],
    "DailyMarket_Incremental": [
        "CDC_FLAG",
        "CDC_DSN",
        "DM_DATE",
        "DM_S_SYMB",
        "DM_CLOSE",
        "DM_HIGH",
        "DM_LOW",
        "DM_VOL",
    ],
    # CashTransaction
    "CashTransaction_Batch1": ["CT_CA_ID", "CT_DTS", "CT_AMT", "CT_NAME"],
    "CashTransaction_Incremental": [
        "CDC_FLAG",
        "CDC_DSN",
        "CT_CA_ID",
        "CT_DTS",
        "CT_AMT",
        "CT_NAME",
    ],
    # FINWIRE
    "FINWIRE_CMP": [
        "PTS",
        "RecType",
        "CompanyName",
        "CIK",
        "Status",
        "IndustryID",
        "SPrating",
        "FoundingDate",
        "AddrLine1",
        "AddrLine2",
        "PostalCode",
        "City",
        "StateProvince",
        "Country",
        "CEOname",
        "Description",
    ],
    "FINWIRE_SEC": [
        "PTS",
        "RecType",
        "Symbol",
        "IssueType",
        "Status",
        "Name",
        "ExID",
        "ShOut",
        "FirstTradeDate",
        "FirstTradeExchg",
        "Dividend",
        "CoNameOrCIK",
    ],
    "FINWIRE_FIN": [
        "PTS",
        "RecType",
        "Year",
        "Quarter",
        "QtrStartDate",
        "PostingDate",
        "Revenue",
        "Earnings",
        "EPS",
        "DilutedEPS",
        "Margin",
        "Inventory",
        "Assets",
        "Liabilities",
        "ShOut",
        "DilutedShOut",
        "CoNameOrCIK",
    ],
}

###############################################################################
# 3. BATCH DEFINITIONS
###############################################################################

BATCHS: Dict[str, List[str]] = {
    "Batch1": [
        "BatchDate.txt",
        "CashTransaction.txt",
        "CustomerMgmt.xml",
        "DailyMarket.txt",
        "Date.txt",
        "FINWIRE1967Q1",
        "HoldingHistory.txt",
        "HR.csv",
        "Industry.txt",
        "Prospect.csv",
        "StatusType.txt",
        "TaxRate.txt",
        "Time.txt",
        "Trade.txt",
        "TradeHistory.txt",
        "TradeType.txt",
        "WatchHistory.txt",
    ],
    "Batch2": [
        "Account.txt",
        "BatchDate.txt",
        "CashTransaction.txt",
        "Customer.txt",
        "DailyMarket.txt",
        "HoldingHistory.txt",
        "Prospect.csv",
        "Trade.txt",
        "WatchHistory.txt",
    ],
    "Batch3": [
        "Account.txt",
        "BatchDate.txt",
        "CashTransaction.txt",
        "Customer.txt",
        "DailyMarket.txt",
        "HoldingHistory.txt",
        "Prospect.csv",
        "Trade.txt",
        "WatchHistory.txt",
    ],
}


###############################################################################
# 4. FILE READERS
###############################################################################


def read_csv_file(path: Path) -> pd.DataFrame:
    """Reads a comma-separated CSV file."""
    return pd.read_csv(path, header=None, dtype=str)


def read_pipe_file(path: Path) -> pd.DataFrame:
    """Reads a pipe-separated flat file."""
    return pd.read_csv(path, sep="|", header=None, dtype=str)


def read_batch_date(path: Path) -> pd.DataFrame:
    """Reads raw text from a BatchDate file into a single-cell DataFrame."""
    df = pd.DataFrame([[path.read_text().strip()]])
    return df


def read_xml(path: Path) -> None:
    """Parses an XML file and prints out the root tag and its first child."""
    tree = ET.parse(path)
    root = tree.getroot()

    print("=" * 120)
    print(path.name)
    print("=" * 120)
    print("Root:", root.tag)

    first = next(iter(root))
    ET.dump(first)


###############################################################################
# 5. SPECIALIZED INSPECTORS & UTILITIES
###############################################################################


def inspect_finwire(path: Path) -> None:
    """Reads the first 5 rows of a FINWIRE flat file and identifies record schemas."""
    print("=" * 120)
    print(path.name)
    print("=" * 120)

    with open(path, encoding="utf8", errors="ignore") as f:
        for _ in range(5):
            line = f.readline()
            if not line:
                break

            rec = line[15:18]

            if rec == "CMP":
                print("\nRecord Type : CMP")
                print("Expected Columns:")
                print(SCHEMAS["FINWIRE_CMP"])

            elif rec == "SEC":
                print("\nRecord Type : SEC")
                print("Expected Columns:")
                print(SCHEMAS["FINWIRE_SEC"])

            elif rec == "FIN":
                print("\nRecord Type : FIN")
                print("Expected Columns:")
                print(SCHEMAS["FINWIRE_FIN"])

            print("\nActual Record:")
            print(line.rstrip())
            print("-" * 80)


def get_schema(batch: str, filename: str) -> Optional[List[str]]:
    """Determines the correct schema mapping based on the batch and filename."""
    if filename == "Trade.txt":
        return (
            SCHEMAS["Trade_Batch1"]
            if batch == "Batch1"
            else SCHEMAS["Trade_Incremental"]
        )

    if filename == "HoldingHistory.txt":
        return (
            SCHEMAS["HoldingHistory_Batch1"]
            if batch == "Batch1"
            else SCHEMAS["HoldingHistory_Incremental"]
        )

    if filename == "WatchHistory.txt":
        return (
            SCHEMAS["WatchHistory_Batch1"]
            if batch == "Batch1"
            else SCHEMAS["WatchHistory_Incremental"]
        )

    if filename == "DailyMarket.txt":
        return (
            SCHEMAS["DailyMarket_Batch1"]
            if batch == "Batch1"
            else SCHEMAS["DailyMarket_Incremental"]
        )

    if filename == "CashTransaction.txt":
        return (
            SCHEMAS["CashTransaction_Batch1"]
            if batch == "Batch1"
            else SCHEMAS["CashTransaction_Incremental"]
        )

    return SCHEMAS.get(filename)


def validate_dataframe(
    df: pd.DataFrame, expected_columns: List[str], file_path: Union[str, Path]
) -> None:
    """Optional direct validator for DataFrames."""
    expected = len(expected_columns)
    actual = len(df.columns)

    print("=" * 120)
    print(file_path)

    if expected != actual:
        print("❌ COLUMN COUNT MISMATCH")
        print(f"Expected : {expected}")
        print(f"Actual   : {actual}")
        print("\nExpected columns:")
        print(expected_columns)
        print("\nFirst row:")
        print(df.iloc[0].tolist())
        return

    df.columns = expected_columns
    print("✅ MATCH")
    print(df.head())


###############################################################################
# 6. FILE VALIDATION CORE
###############################################################################


def validate_file(batch: str, filename: str) -> None:
    """Locates a batch file, reads its contents, and validates it against its schema."""
    path = ROOT / batch / filename

    print("\n")
    print("=" * 120)
    print(path)
    print("=" * 120)

    # 1. Existence check
    if not path.exists():
        print("❌ File Not Found")
        failed.append(str(path))
        return

    # 2. XML files handling
    if filename == "CustomerMgmt.xml":
        read_xml(path)
        passed.append(filename)
        return

    # 3. FINWIRE files handling
    if filename.startswith("FINWIRE"):
        inspect_finwire(path)
        passed.append(filename)
        return

    # 4. Read standard tabular formats
    if filename.endswith(".csv"):
        df = read_csv_file(path)
    elif filename == "BatchDate.txt":
        df = read_batch_date(path)
    else:
        df = read_pipe_file(path)

    # 5. Fetch and assert schema
    schema = get_schema(batch, filename)
    if schema is None:
        print("❌ No schema defined.")
        failed.append(filename)
        return

    expected = len(schema)
    actual = len(df.columns)

    if expected != actual:
        print("❌ COLUMN COUNT MISMATCH")
        print(f"Expected : {expected}")
        print(f"Actual   : {actual}")
        print("\nExpected Columns")
        print(schema)
        print("\nFirst Row")
        print(df.iloc[0].tolist())
        failed.append(filename)
        return

    df.columns = schema
    print("✅ MATCH")
    print(df.head())
    passed.append(filename)


###############################################################################
# 7. EXECUTION & REPORTING
###############################################################################

if __name__ == "__main__":
    # Process all batches sequentially
    for batch in BATCHS:
        print("\n")
        print("#" * 120)
        print(batch)
        print("#" * 120)

        for filename in BATCHS[batch]:
            validate_file(batch, filename)

    # Final summary output
    print("\n")
    print("=" * 120)
    print("SUMMARY")
    print("=" * 120)
    print(f"Passed : {len(passed)}")
    print(f"Failed : {len(failed)}")

    if failed:
        print("\nFiles with Problems\n")
        for f in failed:
            print(" -", f)
    else:
        print("\n🎉 All files match the documented schemas.")