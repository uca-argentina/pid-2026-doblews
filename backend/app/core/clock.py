"""What day it is, for the people using the application.

A task started "today" is started on the day the architect is living, not on the
server's. The deploy runs in UTC (ADR-008), where the date turns over at 21:00
Argentine time: without this, a task started after dinner would be recorded as
started tomorrow, and refused as a date in the future.
"""

from datetime import date, datetime, timedelta, timezone

# Argentina is UTC-3 all year: it has not observed daylight saving since 2009.
# A fixed offset rather than ZoneInfo("America/Argentina/Buenos_Aires") so this
# does not depend on the container image shipping the tz database. If the
# platform ever serves another country, the zone becomes a column on firm and
# this function takes it as an argument.
LOCAL_ZONE = timezone(timedelta(hours=-3), name="ART")


def today() -> date:
    """Today's calendar date in Argentina."""
    return datetime.now(LOCAL_ZONE).date()
