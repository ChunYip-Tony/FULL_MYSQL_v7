from __future__ import annotations

import os
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

BUSINESS_TIMEZONE=os.environ.get('FULLMYSQL_BUSINESS_TIMEZONE','America/Los_Angeles')


def business_now() -> datetime:
    return datetime.now(ZoneInfo(BUSINESS_TIMEZONE))


def business_today() -> date:
    return business_now().date()


def completed_through_date() -> date:
    return business_today() - timedelta(days=1)
