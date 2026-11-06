"""Shared setup for booking tests: a shop open 09:00 to 17:00 every day, and times a week ahead so
they pass the notice check whenever the tests run."""

from datetime import datetime, time, timedelta

from apps.bookings.slots import market_today, market_zone
from tests.factories import OpeningHoursFactory, ServiceFactory, ServicesShopFactory, UserFactory


def open_every_day(shop, opens_at=time(9), closes_at=time(17)):
    for weekday in range(7):
        OpeningHoursFactory(shop=shop, weekday=weekday, opens_at=opens_at, closes_at=closes_at)


def bookable_service(*, capacity=1, duration=60, shop=None, **shop_fields):
    shop = shop or ServicesShopFactory(booking_capacity=capacity, **shop_fields)
    if not shop.opening_hours.exists():
        open_every_day(shop)
    return ServiceFactory(shop=shop, duration_minutes=duration)


def visit_date(days_ahead=7):
    return market_today() + timedelta(days=days_ahead)


def visit_time(hour=10, minute=0, days_ahead=7):
    return datetime.combine(visit_date(days_ahead), time(hour, minute), tzinfo=market_zone())


def verified_customer():
    return UserFactory(is_email_verified=True)


def request_body(service, starts_at=None, **extra):
    return {
        "service": service.id,
        "starts_at": (starts_at or visit_time()).isoformat(),
        "contact_phone": "+255712345678",
        **extra,
    }
