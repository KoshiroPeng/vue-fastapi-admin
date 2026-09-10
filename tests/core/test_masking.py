import pytest

from app.core.masking import hash_ip, hash_mac, mask_account, mask_ip, mask_mac


def test_mac_hash_is_canonical_scoped_and_non_reversible() -> None:
    secret = "test-only-secret"

    colon_hash = hash_mac("AA:BB:CC:DD:EE:FF", secret)
    dashed_hash = hash_mac("aa-bb-cc-dd-ee-ff", secret)

    assert colon_hash == dashed_hash
    assert len(colon_hash) == 64
    assert "aabbccddeeff" not in colon_hash
    assert colon_hash != hash_ip("170.187.204.221", secret)


def test_identifiers_are_masked_for_display() -> None:
    assert mask_mac("AA-BB-CC-DD-EE-FF") == "AA:**:**:**:**:FF"
    assert mask_ip("10.128.34.56") == "10.***.***.56"
    assert mask_account("sms_13800001234") == "sms_138****1234"
    assert mask_account("kiosk_abcdef123456") == "kio****3456"


@pytest.mark.parametrize("value", ["", "not-a-mac", "AA:BB:CC:DD:EE"])
def test_invalid_mac_is_rejected(value: str) -> None:
    with pytest.raises(ValueError, match="MAC"):
        hash_mac(value, "test-only-secret")
