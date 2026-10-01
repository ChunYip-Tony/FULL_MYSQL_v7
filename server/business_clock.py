from __future__ import annotations

import os
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

BUSINESS_TIMEZONE=os.environ.get('FULLMYSQL_BUSINESS_TIMEZONE','America/Los_Angeles')

try:
    MVT_DAILY_GRACE_HOUR=max(0,min(23,int(os.environ.get('FULLMYSQL_MVT_DAILY_GRACE_HOUR','15'))))
except (TypeError,ValueError):
    MVT_DAILY_GRACE_HOUR=15

try:
    POS_DAILY_GRACE_HOUR=max(0,min(23,int(os.environ.get('FULLMYSQL_POS_DAILY_GRACE_HOUR','15'))))
except (TypeError,ValueError):
    POS_DAILY_GRACE_HOUR=15


def business_now() -> datetime:
    return datetime.now(ZoneInfo(BUSINESS_TIMEZONE))


def business_today() -> date:
    return business_now().date()


def completed_through_date() -> date:
    return business_today() - timedelta(days=1)


def _daily_expected_through_date(grace_hour: int, now: datetime | None = None) -> date:
    current=now or business_now()
    cutoff=current.replace(
        hour=grace_hour,
        minute=0,
        second=0,
        microsecond=0,
    )
    lag_days=1 if current>=cutoff else 2
    return current.date()-timedelta(days=lag_days)


def movement_expected_through_date(now: datetime | None = None) -> date:
    """Latest MVT business date that is operationally due.

    Yesterday's MVT is not required until the local business-day grace cutoff.
    With the default 15:00 cutoff, 00:00-14:59 treats yesterday as PENDING and
    requires coverage only through the day before yesterday. At 15:00 or later,
    yesterday becomes required.
    """
    return _daily_expected_through_date(MVT_DAILY_GRACE_HOUR, now)


def pos_expected_through_date(now: datetime | None = None) -> date:
    """Latest POS sales business date that is operationally due.

    Same operating rule as MVT by default: yesterday's POS file remains PENDING
    until 15:00 local time. If it arrives earlier it is usable immediately, but
    its absence before the cutoff is not a missing-file/data-health condition.
    """
    return _daily_expected_through_date(POS_DAILY_GRACE_HOUR, now)
