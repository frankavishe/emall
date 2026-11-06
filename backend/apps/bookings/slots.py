"""Open times for a service. Opening hours are local wall-clock times in the market's time zone,
so every calculation happens there and the results carry that zone's offset."""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.conf import settings
from django.utils import timezone

from apps.bookings.models import Booking


@dataclass(frozen=True)
class Slot:
    starts_at: datetime
    ends_at: datetime


def market_zone():
    return ZoneInfo(settings.MARKET_TIME_ZONE)


def market_today(now=None):
    return (now or timezone.now()).astimezone(market_zone()).date()


def market_day_bounds(local_date: date) -> tuple[datetime, datetime]:
    """The instants a market date starts and ends, the end being the next day's start."""

    start = datetime.combine(local_date, time.min, tzinfo=market_zone())
    return start, start + timedelta(days=1)


def _peak_overlap(holds, starts_at, ends_at) -> int:
    """The most `holds` running at any one moment of the window. Counting every hold touching the
    window would be wrong: two can both overlap it without overlapping each other."""

    events = []
    for hold_start, hold_end in holds:
        if hold_start < ends_at and hold_end > starts_at:
            events.append((max(hold_start, starts_at), 1))
            events.append((min(hold_end, ends_at), -1))
    # Ends sort before starts at the same moment, so back-to-back holds don't count together.
    events.sort()
    running = peak = 0
    for _, change in events:
        running += change
        peak = max(peak, running)
    return peak


def open_slots(service, local_date: date, *, now=None) -> list[Slot]:
    """The times `service` can start on `local_date`, earliest first: every step within an opening
    period where the whole service fits and the shop has room, at least the minimum notice ahead
    and inside the booking window."""

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
    if not slots:
        return slots

    holds = list(
        Booking.objects.holding(now)
        .filter(shop=shop)
        .overlapping(*market_day_bounds(local_date))
        .values_list("starts_at", "ends_at")
    )
    return [
        slot
        for slot in slots
        if _peak_overlap(holds, slot.starts_at, slot.ends_at) < shop.booking_capacity
    ]
