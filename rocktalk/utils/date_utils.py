from datetime import datetime
from typing import List, Tuple

import pandas as pd
from models.interfaces import ChatSession

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def create_date_masks(
    recent_sessions: List[ChatSession],
) -> Tuple[List[Tuple[str, pd.Series]], pd.DataFrame]:
    """
    Creates time-based masks for a DataFrame containing session data.

    This function takes session data and creates boolean masks to categorize sessions into
    different time periods: Current month, past 11 months, and then by year for older sessions.

    Args:
        recent_sessions (List[ChatSession]): List of ChatSession objects containing session data

    Returns:
        Tuple[List[Tuple[str, pd.Series]], pd.DataFrame]: A tuple containing:
            - List of tuples, where each tuple contains:
                - A string label for the time period (e.g., "July 2023")
                - A boolean mask (pandas Series) indicating which sessions belong to that time period
            - The processed DataFrame of sessions
    """
    # Convert the list of ChatSession objects to a DataFrame
    df_sessions = pd.DataFrame([session.dict() for session in recent_sessions])

    # Ensure datetime columns are in the correct format
    df_sessions["last_active"] = pd.to_datetime(df_sessions["last_active"])
    df_sessions["created_at"] = pd.to_datetime(df_sessions["created_at"])

    now = datetime.now()
    current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    masks = []

    # Create masks for the current month and past 11 months
    for i in range(12):
        month_start = current_month_start - pd.DateOffset(months=i)
        month_end = month_start + pd.DateOffset(months=1)
        month_label = month_start.strftime("%B %Y")

        mask = (df_sessions["last_active"] >= month_start) & (
            df_sessions["last_active"] < month_end
        )
        masks.append((month_label, mask))

    # Create masks for previous years
    oldest_date = df_sessions["last_active"].min()
    current_year = now.year

    for year in range(current_year - 1, oldest_date.year - 1, -1):
        year_start = datetime(year, 1, 1)
        year_end = datetime(year + 1, 1, 1)
        year_mask = (df_sessions["last_active"] >= year_start) & (
            df_sessions["last_active"] < year_end
        )

        if year_mask.any():
            masks.append((str(year), year_mask))

    return masks, df_sessions
