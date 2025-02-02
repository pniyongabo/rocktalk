from datetime import datetime, timezone
from typing import Optional

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S.%f%z"  # Updated to include timezone offset
DATE_FORMAT = "%Y-%m-%d"


def format_datetime(dt: Optional[datetime] = None) -> str:
    """Format a datetime object to string using standard format.
    If no datetime provided, uses current time. Ensures datetime is timezone-aware.

    Args:
        dt: datetime object

    Returns:
        String representation of datetime with timezone info
    """
    if dt is None:
        dt = datetime.now(timezone.utc)
    elif dt.tzinfo is None:
        # Assume naive datetime is UTC
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.strftime(DATETIME_FORMAT)


def parse_datetime(dt_string: str) -> datetime:
    """Parse a datetime string in our standard format.
    Handles both timezone-aware and naive datetime strings.

    Args:
        dt_string: String representation of datetime

    Returns:
        datetime object
    """
    try:
        # Try parsing with microseconds and timezone info
        return datetime.strptime(dt_string, "%Y-%m-%d %H:%M:%S.%f%z")
    except ValueError:
        try:
            # Try parsing with microseconds but without timezone
            dt = datetime.strptime(dt_string, "%Y-%m-%d %H:%M:%S.%f")
        except ValueError:
            try:
                # Try parsing without microseconds and without timezone
                dt = datetime.strptime(dt_string, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                try:
                    # Try parsing without microseconds but with timezone
                    dt = datetime.strptime(dt_string, "%Y-%m-%d %H:%M:%S%z")
                except ValueError:
                    # Handle other possible formats as needed
                    raise ValueError(f"Failed to parse datetime string: {dt_string}")
        # Assume naive datetime is in UTC
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
