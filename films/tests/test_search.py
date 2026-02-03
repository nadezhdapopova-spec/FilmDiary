from unittest.mock import Mock

import pytest

from films.models import UserFilm
from films.services.search import (
    search_favorite_films,
    search_films,
    search_tmdb_film,
    search_user_film,
)


@pytest.mark.django_db
def test_search_tmdb_film_empty_query(user):
    """Проверяет результат поискового запроса в TMDB: пустой при пустом запросе"""
    assert search_tmdb_film("", user) == []


@pytest.mark.django_db
def test_search_films_router_tmdb(monkeypatch, user):
    """Если у пользователя сохранен фильм в БД, ищет в БД"""
    monkeypatch.setattr("films.services.search.search_tmdb_film", lambda q, u, p: ["ok"])
    assert search_films("q", user) == ["ok"]


@pytest.mark.django_db
def test_search_films_empty(user):
    """Проверяет пустой запрос"""
    assert search_films("", user) == []


@pytest.mark.django_db
def test_search_user_film_not_found(user):
    """Тест поиска несуществующего фильма."""
    result = search_user_film("nonexistent", user)
    assert result == []


@pytest.mark.django_db
def test_search_favorite_films_not_favorite(user, film):
    """Тест не любимого фильма"""
    UserFilm.objects.create(user=user, film=film, is_favorite=False)
    result = search_favorite_films("Test", user)
    assert result == []


def test_search_films_empty_query():
    """Тест пустого запроса"""
    result = search_films("", Mock())
    assert result == []


def test_search_films_tmdb_default(monkeypatch, user):
    """Тест TMDB по умолчанию"""
    _ = Mock()
    monkeypatch.setattr("films.services.search.search_tmdb_film", lambda q, u, p: ["tmdb result"])

    result = search_films("test", user)
    assert result == ["tmdb result"]
