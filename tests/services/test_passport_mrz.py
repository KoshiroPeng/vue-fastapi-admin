from app.services.passport.mrz import validate_mrz_check_digit


def test_icao_mrz_check_digit() -> None:
    assert validate_mrz_check_digit("L898902C3", "6")
    assert not validate_mrz_check_digit("L898902C3", "7")
