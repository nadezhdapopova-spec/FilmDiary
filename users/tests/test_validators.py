import pytest
from django.core.exceptions import ValidationError

from users.validators import validate_telegram_id


def test_validate_telegram_id_invalid():
    """Невалидный Telegram ID: содержит буквы"""
    with pytest.raises(ValidationError):
        validate_telegram_id("abc123")

@pytest.mark.django_db
def test_validate_telegram_id_valid():
    """Корректный Telegram ID проходит валидацию"""
    assert validate_telegram_id(123456789) == 123456789


@pytest.mark.django_db
def test_validate_telegram_id_too_short():
    """Невалидный Telegram ID: недостаточно символов"""
    with pytest.raises(ValidationError):
        validate_telegram_id(1234)


@pytest.mark.django_db
def test_validate_telegram_id_too_long():
    """Невалидный Telegram ID: больше символов"""
    with pytest.raises(ValidationError):
        validate_telegram_id(1234567890123)
