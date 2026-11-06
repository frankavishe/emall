"""Open times for a service. Opening hours are local wall-clock times in the market's time zone,
so every calculation happens there and the results carry that zone's offset."""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from django.conf import settings
from django.utils import timezone


@dataclass(frozen=True)
class Slot:
    starts_at: datetime
    ends_at: datetime


def market_zone():
    return ZoneInfo(settings.MARKET_TIME_ZONE)


def market_today(now=None):
    return (now or timezone.now()).astimezone(market_zone()).date()


def open_slots(service, local_date: date, *, now=None) -> list[Slot]:
    """The times `service` can start on `local_date`, earliest first: every step within an opening
    period where the whole service fits, at least the minimum notice ahead and inside the booking
    window."""

    now = now or timezone.now()
    today = market_today(now)
    last_day = today + timedelta(days=settings.BOOKING_MAX_ADVANCE_DAYS)
    if local_date < today or local_date > last_day:
        return []

    shop = service.shop
    if shop.closures.filter(date=local_date).exists():
        return []

    zone = market_zone()
    earliest = now + timedelta(hours=settings.BOOKING_MIN_NOTICE_HOURS)
    step = timedelta(minutes=settings.BOOKING_SLOT_MINUTES)
    duration = timedelta(minutes=service.duration_minutes)

    slots = []
    for period in shop.opening_hours.filter(weekday=local_date.weekday()).order_by("opens_at"):
        start = datetime.combine(local_date, period.opens_at, tzinfo=zone)
        closes = datetime.combine(local_date, period.closes_at, tzinfo=zone)
        while start + duration <= closes:
            if start >= earliest:
                slots.append(Slot(starts_at=start, ends_at=start + duration))
            start += step
    return slots
