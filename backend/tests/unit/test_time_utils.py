import sys
from datetime import datetime
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.utils.time_utils import COLOMBIA_TZ, get_today_str, to_colombia_time


def test_to_colombia_time_localizes_naive_datetime_as_utc() -> None:
    naive_dt = datetime(2026, 3, 28, 12, 0, 0)

    converted = to_colombia_time(naive_dt)

    assert converted.tzinfo is not None
    assert converted.tzinfo.zone == COLOMBIA_TZ.zone
    # 12:00 UTC -> 07:00 America/Bogota
    assert converted.hour == 7


def test_to_colombia_time_converts_aware_datetime() -> None:
    aware_dt = COLOMBIA_TZ.localize(datetime(2026, 3, 28, 9, 30, 0))

    converted = to_colombia_time(aware_dt)

    assert converted.tzinfo is not None
    assert converted.tzinfo.zone == COLOMBIA_TZ.zone
    assert converted.hour == 9
    assert converted.minute == 30


def test_get_today_str_returns_iso_date() -> None:
    today_str = get_today_str()

    parsed = datetime.strptime(today_str, "%Y-%m-%d")
    assert parsed.strftime("%Y-%m-%d") == today_str
