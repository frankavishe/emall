"""Open times, through `open_slots` directly for edge cases and the public endpoint for shape."""

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest

from apps.bookings.slots import open_slots
from tests.factories import (
    OpeningHoursFactory,
    ServiceFactory,
    ServicesShopFactory,
    ShopClosureFactory,
)

pytestmark = pytest.mark.django_db

DAR = ZoneInfo("Africa/Dar_es_Salaam")
# A Monday. `NOW` is the Friday before, midday in Dar es Salaam.
MONDAY = date(2030, 1, 7)
NOW = datetime(2030, 1, 4, 12, 0, tzinfo=DAR)


def _service(duration=60, capacity=1):
    shop = ServicesShopFactory(booking_capacity=capacity)
    return ServiceFactory(shop=shop, duration_minutes=duration)


def _local_times(slots):
    return [slot.starts_at.astimezone(DAR).strftime("%H:%M") for slot in slots]


def test_steps_through_the_period_and_the_whole_service_fits_before_closing():
    service = _service(duration=60)
    OpeningHoursFactory(shop=service.shop, weekday=0, opens_at=time(9), closes_at=time(11))

    assert _local_times(open_slots(service, MONDAY, now=NOW)) == ["09:00", "09:30", "10:00"]


def test_last_start_for_an_ordinary_day():
    service = _service(duration=60)
    OpeningHoursFactory(shop=service.shop, weekday=0)

    assert _local_times(open_slots(service, MONDAY, now=NOW))[-1] == "16:00"


def test_each_slot_ends_after_the_service_duration():
    service = _service(duration=90)
    OpeningHoursFactory(shop=service.shop, weekday=0, opens_at=time(9), closes_at=time(11))

    slot = open_slots(service, MONDAY, now=NOW)[0]
    assert slot.ends_at - slot.starts_at == timedelta(minutes=90)


def test_multiple_periods_leave_the_gap_unoffered():
    service = _service(duration=60)
    OpeningHoursFactory(shop=service.shop, weekday=0, opens_at=time(9), closes_at=time(10))
    OpeningHoursFactory(shop=service.shop, weekday=0, opens_at=time(13), closes_at=time(14))

    assert _local_times(open_slots(service, MONDAY, now=NOW)) == ["09:00", "13:00"]


def test_a_service_too_long_for_a_period_is_not_offered_in_it():
    service = _service(duration=120)
    OpeningHoursFactory(shop=service.shop, weekday=0, opens_at=time(9), closes_at=time(10))

    assert open_slots(service, MONDAY, now=NOW) == []


def test_another_weekday_has_no_times():
    service = _service()
    OpeningHoursFactory(shop=service.shop, weekday=1)

    assert open_slots(service, MONDAY, now=NOW) == []


def test_closure_offers_nothing():
    service = _service()
    OpeningHoursFactory(shop=service.shop, weekday=0)
    ShopClosureFactory(shop=service.shop, date=MONDAY)

    assert open_slots(service, MONDAY, now=NOW) == []


def test_minimum_notice_hides_times_that_are_too_soon():
    service = _service(duration=60)
    OpeningHoursFactory(shop=service.shop, weekday=0, opens_at=time(9), closes_at=time(14))
    now = datetime(2030, 1, 7, 9, 0, tzinfo=DAR)

    # Three hours from 09:00 is 12:00, which is still offered.
    assert _local_times(open_slots(service, MONDAY, now=now)) == [
        "12:00",
        "12:30",
        "13:00",
    ]


def test_past_dates_offer_nothing():
    service = _service()
    OpeningHoursFactory(shop=service.shop, weekday=0)

    assert open_slots(service, MONDAY, now=datetime(2030, 1, 8, 12, tzinfo=DAR)) == []


def test_booking_window_includes_day_60_but_not_day_61():
    service = _service()
    for weekday in range(7):
        OpeningHoursFactory(shop=service.shop, weekday=weekday)
    today = NOW.date()

    assert open_slots(service, today + timedelta(days=60), now=NOW)
    assert open_slots(service, today + timedelta(days=61), now=NOW) == []


def test_times_are_in_the_market_zone_when_the_utc_date_differs():
    """22:30 UTC on Sunday is already 01:30 on Monday in Dar es Salaam."""

    service = _service(duration=60)
    OpeningHoursFactory(shop=service.shop, weekday=0, opens_at=time(9), closes_at=time(10))
    now = datetime(2030, 1, 6, 22, 30, tzinfo=UTC)

    slots = open_slots(service, MONDAY, now=now)

    assert _local_times(slots) == ["09:00"]
    assert slots[0].starts_at == datetime(2030, 1, 7, 6, 0, tzinfo=UTC)


def test_opening_hours_near_midnight_stay_on_the_local_date():
    service = _service(duration=60)
    OpeningHoursFactory(shop=service.shop, weekday=0, opens_at=time(0), closes_at=time(1))

    slots = open_slots(service, MONDAY, now=NOW)

    # 00:00 on Monday in Dar es Salaam is 21:00 on Sunday in UTC.
    assert slots[0].starts_at == datetime(2030, 1, 6, 21, 0, tzinfo=UTC)


def test_endpoint_returns_times_with_the_market_offset(api_client):
    service = _service(duration=60)
    OpeningHoursFactory(shop=service.shop, weekday=0, opens_at=time(9), closes_at=time(10))
    # Far enough ahead to pass the notice check whenever the test runs.
    target = date.today() + timedelta(days=7)
    target -= timedelta(days=target.weekday())
    target += timedelta(days=7)

    response = api_client.get(f"/api/catalog/services/{service.id}/slots?date={target.isoformat()}")

    assert response.status_code == 200
    assert response.data["date"] == target.isoformat()
    assert response.data["time_zone"] == "Africa/Dar_es_Salaam"
    assert response.data["slots"] == [
        {
            "starts_at": f"{target.isoformat()}T09:00:00+03:00",
            "ends_at": f"{target.isoformat()}T10:00:00+03:00",
        }
    ]


@pytest.mark.parametrize("bad_date", ["", "tomorrow", "2030-13-45"])
def test_endpoint_rejects_a_bad_date(api_client, bad_date):
    service = _service()

    response = api_client.get(f"/api/catalog/services/{service.id}/slots?date={bad_date}")

    assert response.status_code == 400


def test_endpoint_hides_an_unpublished_service(api_client):
    service = ServiceFactory(is_published=False)

    response = api_client.get(f"/api/catalog/services/{service.id}/slots?date=2030-01-07")

    assert response.status_code == 404
