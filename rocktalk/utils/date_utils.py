# Import required datetime classes for time-based operations
from datetime import datetime, timedelta

# Import pandas library with alias 'pd' for data manipulation and analysis
import pandas as pd
from .datetime_utils import DATETIME_FORMAT


def create_date_masks(
    recent_sessions: pd.DataFrame,
) -> tuple[list[tuple[str, pd.Series]], pd.DataFrame]:
    """
    Creates time-based masks for a DataFrame containing session data.

    This function takes session data and creates boolean masks to categorize sessions into
    different time periods: Today, Yesterday, This Week, This Month, Last 6 Months,
    Last Year, and Older.

    Args:
        recent_sessions (pd.DataFrame): DataFrame containing session data with 'last_active' column
                                      The 'last_active' column should contain timestamp information
                                      for when each session was last active.

    Returns:
        tuple[list[tuple[str, pd.Series]], pd.DataFrame]: A tuple containing:
            - List of tuples, where each tuple contains:
                - A string label for the time period (e.g., "Today")
                - A boolean mask (pandas Series) indicating which sessions belong to that time period
            - The processed and sorted DataFrame of sessions
    """
    # Convert input to DataFrame format if it isn't already
    # This ensures consistent data handling regardless of input format
    df_sessions = pd.DataFrame(recent_sessions)

    # Convert 'last_active' column to datetime format
    # This enables datetime operations and comparisons on the timestamps
    df_sessions["last_active"] = pd.to_datetime(
        df_sessions["last_active"], format=DATETIME_FORMAT
    )

    # Sort sessions by date in descending order (newest to oldest)
    # This aids in chronological organization and potential performance optimizations
    df_sessions = df_sessions.sort_values("last_active", ascending=False)

    # Get current timestamp and extract current date
    # Using pandas Timestamp for consistency with DataFrame operations
    now = pd.Timestamp.now()
    today = now.date()

    # Create masks for different time periods
    # Each mask is a boolean Series where True indicates the session belongs to that period

    # Today's sessions: Sessions that occurred on the current date
    today_mask = df_sessions["last_active"].dt.date == today

    # Yesterday's sessions: Sessions that occurred exactly one day ago
    yesterday_mask = df_sessions["last_active"].dt.date == (today - timedelta(days=1))

    # This week's sessions: Sessions from the past 7 days, excluding today and yesterday
    # The complex condition ensures no overlap with today and yesterday masks
    this_week_mask = (
        (df_sessions["last_active"].dt.date > (today - timedelta(days=7)))
        & (~today_mask)
        & (~yesterday_mask)
    )

    # This month's sessions: Sessions from the past 30 days, excluding more recent periods
    # Uses multiple conditions to prevent overlap with other time periods
    this_month_mask = (
        (df_sessions["last_active"].dt.date > (today - timedelta(days=30)))
        & (~today_mask)
        & (~yesterday_mask)
        & (~this_week_mask)
    )

    # Last 6 months' sessions: Sessions from the past 180 days, excluding more recent periods
    six_months_mask = (
        (df_sessions["last_active"].dt.date > (today - timedelta(days=180)))
        & (~today_mask)
        & (~yesterday_mask)
        & (~this_week_mask)
        & (~this_month_mask)
    )

    # Last year's sessions: Sessions from the past 365 days, excluding more recent periods
    last_year_mask = (
        (df_sessions["last_active"].dt.date > (today - timedelta(days=365)))
        & (~today_mask)
        & (~yesterday_mask)
        & (~this_week_mask)
        & (~this_month_mask)
        & (~six_months_mask)
    )

    # Older sessions: Any sessions older than 1 year
    # Simple comparison to find all sessions before the 365-day cutoff
    older_mask = df_sessions["last_active"].dt.date <= (today - timedelta(days=365))

    # Return both the masks and the processed DataFrame
    # Masks are returned as tuples containing a descriptive label and the boolean mask
    return [
        ("Today", today_mask),
        ("Yesterday", yesterday_mask),
        ("This Week", this_week_mask),
        ("This Month", this_month_mask),
        ("Last 6 Months", six_months_mask),
        ("Last Year", last_year_mask),
        ("Older", older_mask),
    ], df_sessions
