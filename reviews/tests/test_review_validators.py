from django.core.exceptions import ValidationError

import pytest

from reviews.validators import validate_number_of_views


def test_validate_number_of_views_ok():
    """Положительное целое число проходит валидацию"""
    validate_number_of_views(5)


def test_validate_number_of_views_none():
    """None допустим"""
    validate_number_of_views(None)


def test_validate_number_of_views_not_int():
    """Нецелое значение вызывает ошибку"""
    with pytest.raises(ValidationError):
        validate_number_of_views("5")


def test_validate_number_of_views_negative():
    """Отрицательное значение запрещено"""
    with pytest.raises(ValidationError):
        validate_number_of_views(-1)
