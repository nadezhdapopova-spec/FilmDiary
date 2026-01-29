from unittest.mock import Mock

import pytest

from films.services.user_film_services import get_user_film, map_status, get_user_recommendations


@pytest.mark.django_db
def test_get_user_film_authenticated(user, film, user_film):
    """Проверяет, что возвращает фильм, если пользователь авторизован и имеет данный фильм в коллекции"""
    assert get_user_film(user, film) == user_film

def test_get_user_film_anon(anon_user, film):
    """Проверяет, что не возвращает фильм, если он отсутствует у пользователя в коллекции"""
    assert get_user_film(anon_user, film) is None

def test_map_status_no_user_film():
    """Проверяет формирование пользовательского статуса фильма, если фильм/отзыв/рейтинг не указан"""
    data = map_status(None, False, None)
    assert data["is_favorite"] is False
    assert data["has_review"] is False

def test_map_status_with_review_high(user_film):
    """Проверяет корректное формирование пользовательского статуса фильма: высокий рейтинг"""
    data = map_status(user_film, True, 9.0)
    assert data["rating_color"] == "high"

def test_map_status_with_review_medium(user_film):
    """Проверяет корректное формирование пользовательского статуса фильма: средний рейтинг"""
    data = map_status(user_film, True, 7.0)
    assert data["rating_color"] == "medium"

def test_map_status_with_review_low(user_film):
    """Проверяет корректное формирование пользовательского статуса фильма: низкий рейтинг"""
    data = map_status(user_film, True, 4.0)
    assert data["rating_color"] == "low"

def test_map_status_with_review_not_rating(user_film):
    """Проверяет корректное формирование пользовательского статуса фильма: нет рейтинга"""
    data = map_status(user_film, True, None)
    assert data["rating_color"] == "medium"

def test_get_user_recommendations_anon(anon_user):
    """Тест неаутентифицированного пользователя"""
    result = get_user_recommendations(anon_user)
    assert result == []

def test_get_user_recommendations_cache_hit(monkeypatch):
    """Тест кэша рекомендаций"""
    mock_user = Mock(is_authenticated=True, id=1)
    mock_cache = Mock(return_value=["rec1", "rec2"])
    monkeypatch.setattr("django.core.cache.cache.get", mock_cache)

    result = get_user_recommendations(mock_user, limit=1)
    mock_cache.assert_called_once_with("recs:user:1", [])
    assert result == ["rec1"]

def test_get_user_recommendations_no_cache(monkeypatch):
    """Тест пустого кэша"""
    mock_user = Mock(is_authenticated=True, id=1)
    monkeypatch.setattr("django.core.cache.cache.get", lambda k, d: None)

    result = get_user_recommendations(mock_user)
    assert result == None


def test_get_user_recommendations_limit(monkeypatch):
    """limit обрезает список"""
    mock_user = Mock(is_authenticated=True, id=1)
    monkeypatch.setattr("django.core.cache.cache.get", lambda k, d: ["a", "b", "c"])

    result = get_user_recommendations(mock_user, limit=2)
    assert result == ["a", "b"]
