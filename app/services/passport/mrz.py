_WEIGHTS = (7, 3, 1)


def _mrz_value(character: str) -> int:
    if character.isdigit():
        return int(character)
    if "A" <= character <= "Z":
        return ord(character) - ord("A") + 10
    if character == "<":
        return 0
    raise ValueError("MRZ 包含非法字符")


def validate_mrz_check_digit(data: str, check_digit: str) -> bool:
    if len(check_digit) != 1 or not check_digit.isdigit():
        return False
    total = sum(_mrz_value(character) * _WEIGHTS[index % 3] for index, character in enumerate(data.upper()))
    return total % 10 == int(check_digit)
