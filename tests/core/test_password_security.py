import pytest
from pydantic import ValidationError

from app.schemas.users import UpdatePassword, UserCreate
from app.utils.password import generate_password


def test_generated_temporary_password_is_strong_and_non_default() -> None:
    password = generate_password()

    assert len(password) >= 16
    assert password != "123456"
    assert any(char.islower() for char in password)
    assert any(char.isupper() for char in password)
    assert any(char.isdigit() for char in password)


def test_new_and_changed_passwords_reject_weak_values() -> None:
    with pytest.raises(ValidationError):
        UserCreate(email="user@example.com", username="user", password="123456")
    with pytest.raises(ValidationError):
        UpdatePassword(old_password="123456", new_password="123456")
