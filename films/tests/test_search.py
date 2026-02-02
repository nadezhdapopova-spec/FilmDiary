from unittest.mock import Mock

import pytest

from films.models import Film, UserFilm
from films.services.search import (
    search_favorite_films,
    search_films,
    search_reviewed_films,
    search_tmdb_film,
    search_user_film,
    search_watched_films,
)


@pytest.mark.django_db
def test_search_tmdb_film_empty_query(user):
    """Проверяет результат поискового запроса в TMDB: пустой при пустом запросе"""
    assert search_tmdb_film("", user) == []


def test_search_tmdb_film_results(monkeypatch, user):
    """Проверяет результат поискового запроса в TMDB"""
    monkeypatch.setattr(
        "films.services.search.tmdb.search_movie",
        lambda query, page: {
            "results": [
                {
                    "id": 1,
                    "title": "TMDB",
                    "genre_ids": [],
                    "vote_average": 5.0,
                }
            ]
        },
    )

    films = search_tmdb_film("test", user)

    assert len(films) == 1
    assert films[0]["title"] == "TMDB"


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
def test_search_user_film_found(user, film, user_film):
    """Поиск существующего фильма пользователя"""
    from films.models import Film

    film2 = Film.objects.create(tmdb_id=101, title="Test film 2")
    UserFilm.objects.create(user=user, film=film2)

    result = search_user_film("test", user, page_num=1)

    assert len(result) == 2
    titles = [uf.film.title for uf in result]
    assert "Test film 2" in titles
    assert "Test film" in titles


@pytest.mark.django_db
def test_search_user_film_not_found(user):
    """Тест поиска несуществующего фильма."""
    result = search_user_film("nonexistent", user)
    assert result == []


@pytest.mark.django_db
def test_search_user_film_pagination(user, film, user_film):
    """Тест пагинации: создаем 13 фильмов для проверки пагинации (12 на страницу)"""
    for i in range(12):
        test_film = Film.objects.create(tmdb_id=200 + i, title=f"Test film {i}")
        UserFilm.objects.create(user=user, film=test_film)

    result_page1 = search_user_film("test", user, 1)
    result_page2 = search_user_film("test", user, 2)

    assert len(result_page1) == 12
    assert len(result_page2) == 1


@pytest.mark.django_db
def test_search_favorite_films_found(user_film):
    """Тест поиска любимого фильма"""
    result = search_favorite_films("Test", user_film.user)
    assert len(result) == 1
    assert result[0].is_favorite is True


@pytest.mark.django_db
def test_search_favorite_films_not_favorite(user, film):
    """Тест не любимого фильма"""
    UserFilm.objects.create(user=user, film=film, is_favorite=False)
    result = search_favorite_films("Test", user)
    assert result == []


@pytest.mark.django_db
def test_search_watched_films(monkeypatch, user, film):
    """Тест с мок queryset'ом Review"""
    mock_qs = Mock()
    mock_qs.filter.return_value.select_related.return_value.prefetch_related.return_value.order_by.return_value = [
        Mock(user=user, film=film, created_at="2024-01-01")
    ]
    mock_qs.side_effect = lambda slice: [mock_qs[0]] if slice == slice(0, 12) else []

    monkeypatch.setattr("reviews.models.Review.objects", mock_qs)

    result = search_watched_films("Test", user)
    assert len(result) == 1
    assert result[0].film == film


@pytest.mark.django_db
def test_search_reviewed_films(monkeypatch, user, film):
    """Тест фильтрации по непустым отзывам"""
    mock_qs = Mock()
    mock_qs.filter.return_value.exclude.return_value.exclude.return_value.select_related.return_value.prefetch_related.return_value.order_by.return_value = ([])  # noqa E501
    monkeypatch.setattr("reviews.models.Review.objects", mock_qs)

    result = search_reviewed_films("Test", user)
    assert result == []


def test_search_films_empty_query():
    """Тест пустого запроса"""
    result = search_films("", Mock())
    assert result == []


@pytest.mark.django_db
def test_search_films_user_films(monkeypatch, user):
    """Тест source='user_films'"""
    mock_result = [Mock()]
    monkeypatch.setattr("films.services.search.search_user_film", lambda q, u, p: mock_result)

    result = search_films("test", user, source="user_films")
    assert result == mock_result


def test_search_films_tmdb_default(monkeypatch, user):
    """Тест TMDB по умолчанию"""
    _ = Mock()
    monkeypatch.setattr("films.services.search.search_tmdb_film", lambda q, u, p: ["tmdb result"])

    result = search_films("test", user)
    assert result == ["tmdb result"]
