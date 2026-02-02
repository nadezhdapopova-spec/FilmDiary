import pytest


@pytest.mark.django_db
def test_user_str(user):
    """Проверка поля username"""
    assert str(user) == user.username


@pytest.mark.django_db
def test_user_default_fields(user):
    """Проверка поле с дефолтными значениями"""
    assert user.email_confirmed is True
    assert user.timezone == "Europe/Moscow"
    assert user.is_blocked is False
