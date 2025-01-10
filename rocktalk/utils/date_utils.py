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
    Groups sessions into:
    - Today (MM/DD/YYYY)
    - Yesterday (MM/DD/YYYY)
    - This Week (MM/DD - MM/DD/YYYY)
    - Earlier This Month (Month YYYY)
    - Previous months (Month YYYY)
    - Over a year ago
    """
    df_sessions = pd.DataFrame([session.model_dump() for session in recent_sessions])

    # Ensure datetime columns are in the correct format
    df_sessions["last_active"] = pd.to_datetime(df_sessions["last_active"])
    df_sessions["created_at"] = pd.to_datetime(df_sessions["created_at"])

    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - pd.Timedelta(days=1)
    week_start = today_start - pd.Timedelta(days=7)  # today_start.weekday()
    month_start = today_start.replace(day=1)
    year_ago = today_start - pd.DateOffset(years=1)

    masks = []
    already_grouped = pd.Series(False, index=df_sessions.index)

    # Today's sessions
    today_mask = df_sessions["last_active"] >= today_start
    if today_mask.any():
        today_label = f"Today ({today_start.strftime('%m/%d/%Y')})"
        masks.append((today_label, today_mask))
        already_grouped |= today_mask

    # Yesterday's sessions
    yesterday_mask = (
        (df_sessions["last_active"] >= yesterday_start)
        & (df_sessions["last_active"] < today_start)
        & ~already_grouped
    )
    if yesterday_mask.any():
        yesterday_label = f"Yesterday ({yesterday_start.strftime('%m/%d/%Y')})"
        masks.append((yesterday_label, yesterday_mask))
        already_grouped |= yesterday_mask

    # This week's sessions (excluding today and yesterday)
    week_mask = (
        (df_sessions["last_active"] >= week_start)
        & (df_sessions["last_active"] < yesterday_start)
        & ~already_grouped
    )
    if week_mask.any():
        week_label = f"Past Week ({week_start.strftime('%m/%d')} - {yesterday_start.strftime('%m/%d/%Y')})"
        masks.append((week_label, week_mask))
        already_grouped |= week_mask

    # This month's sessions (excluding already grouped sessions)
    month_mask = (
        (df_sessions["last_active"] >= month_start)
        & (df_sessions["last_active"] < today_start)
        & ~already_grouped
    )
    if month_mask.any():
        month_label = f"Earlier This Month ({month_start.strftime('%b %Y')})"
        masks.append((month_label, month_mask))
        already_grouped |= month_mask

    # Create masks for previous 11 months
    for i in range(1, 12):
        period_end = month_start - pd.DateOffset(months=i - 1)
        period_start = month_start - pd.DateOffset(months=i)
        month_label = period_start.strftime("%b %Y")

        month_mask = (
            (df_sessions["last_active"] >= period_start)
            & (df_sessions["last_active"] < period_end)
            & ~already_grouped
        )

        # Always append the month even if empty to maintain consistency
        masks.append((month_label, month_mask))
        if month_mask.any():
            already_grouped |= month_mask

    # Over a year ago
    older_mask = (df_sessions["last_active"] < year_ago) & ~already_grouped
    if older_mask.any():
        oldest_date = df_sessions[older_mask]["last_active"].min()
        newest_date = df_sessions[older_mask]["last_active"].max()
        older_label = f"Over a year ago ({oldest_date.strftime('%m/%d/%Y')} - {newest_date.strftime('%m/%d/%Y')})"
        masks.append((older_label, older_mask))

    return masks, df_sessions
