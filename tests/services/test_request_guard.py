import pytest

from app.services.risk_control import RequestExpired, validate_request_timestamp


def test_timestamp_inside_allowed_clock_skew_is_accepted() -> None:
    validate_request_timestamp(timestamp=1_000, now=1_100, max_skew_seconds=300)


@pytest.mark.parametrize("timestamp", [699, 1301])
def test_timestamp_outside_allowed_clock_skew_is_rejected(timestamp: int) -> None:
    with pytest.raises(RequestExpired):
        validate_request_timestamp(timestamp=timestamp, now=1_000, max_skew_seconds=300)
