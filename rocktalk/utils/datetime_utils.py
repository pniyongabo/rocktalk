from datetime import datetime
from typing import Optional

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S.%f"
DATE_FORMAT = "%Y-%m-%d"


def parse_datetime_string(date_string: str) -> datetime:
    """
    Parse a datetime string into a datetime object using the standard format.

    Args:
        date_string: String representation of datetime

    Returns:
        datetime object
    """
    return datetime.strptime(date_string, DATETIME_FORMAT)


def format_datetime(dt: Optional[datetime] = None) -> str:
    """
    Format a datetime object to string using standard format.
    If no datetime provided, uses current time.
    """
    if dt is None:
        dt = datetime.now()
    return dt.strftime(DATETIME_FORMAT)


def parse_datetime(dt_string: str) -> datetime:
    """
    Parse a datetime string in our standard format.
    """
    try:
        return datetime.strptime(dt_string, DATETIME_FORMAT)
    except ValueError:
        # Handle case where microseconds are not present
        return datetime.strptime(dt_string, "%Y-%m-%d %H:%M:%S")
