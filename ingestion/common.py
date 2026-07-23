"""
Shared helpers used across all bronze loaders: type casters, the row-hash
function, and the CSV normalization writer used to stage rows for
COPY INTO (Snowflake loads via stage + COPY INTO, not
row-by-row INSERT).

Function Summary:
- compute_row_hash(values): Generates a deterministic 64-bit integer hash from a list of business column values.
- format_csv_value(value): Renders a Python value into the exact string form the Snowflake
    file format (ff_bronze_csv) expects: ISO dates, ISO-ish timestamps, TRUE/FALSE for booleans, empty string for NULL.
- write_staging_csv(path, rows): Writes a list of rows to a CSV file at the given path, formatting each value appropriately for Snowflake ingestion.
- _safe_cast(raw, caster): Safely casts a raw string value to a target type using the provided caster function, returning None for empty or invalid values.
"""
import csv
import hashlib
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Callable, Iterable, List, Optional, Sequence


def compute_row_hash(values: Sequence[Any]) -> int:
    """
    Generate a deterministic 64-bit integer hash from a list of business column values.
    """
    joined = "|".join("" if v is None else str(v) for v in values).encode("utf-8")
    digest = hashlib.sha256(joined).digest()
    return int.from_bytes(digest[:8], byteorder="big", signed=False)


# Standard Caster Lambdas
parse_date = lambda v: datetime.strptime(v, "%Y-%m-%d").date()
parse_datetime = lambda v: datetime.strptime(v, "%Y-%m-%d %H:%M:%S")
parse_bool = lambda v: v in ("1", "true", "True", "Y", "y")
parse_yyyymmdd = lambda v: None if set(v) == {"0"} else datetime.strptime(v, "%Y%m%d").date()


def format_csv_value(value: Any) -> str:
    """
    Render a Python value into the exact string form the Snowflake file
    format (ff_bronze_csv) expects: ISO dates, ISO-ish timestamps,
    TRUE/FALSE for booleans, empty string for NULL (matches NULL_IF=('')
    and EMPTY_FIELD_AS_NULL=TRUE in the file format DDL).
    """
    if value is None:
        return ""
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return str(value)


def write_staging_csv(path: str, rows: Iterable[Sequence[Any]]) -> int:
    """
    Writes rows to a CSV file using optimal inner-list formatting for speed 
    and outer-generator streaming for O(1) memory safety.
    """
    count = 0
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=",", quoting=csv.QUOTE_MINIMAL)
        
        def stream_and_count():
            nonlocal count
            for row in rows:
                count += 1
                yield [format_csv_value(v) for v in row]

        # Streaming Hybrid: Memory-safe and C-level fast for CPython
        writer.writerows(stream_and_count())

    return count


def _safe_cast(raw: Any, caster: Callable[[str], Any]) -> Optional[Any]:
    """
    Safely casts a raw value using the provided caster function, 
    returning None for empty or invalid values.
    """
    if raw is None:
        return None
    
    raw = str(raw).strip()
    if raw == "":
        return None
        
    try:
        return caster(raw)
    except Exception:
        return None