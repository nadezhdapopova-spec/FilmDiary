import pytest

from films.services.context import build_film_context


@pytest.mark.django_db
def test_build_film_context_db(film):
    """Проверяет формирование контекста для шаблона film_detail.html из БД"""
    context = build_film_context(film=film)

    assert context["source"] == "db"
    assert context["title"] == film.title


def test_build_film_context_tmdb():
    """Проверяет формирование контекста для шаблона film_detail.html из TMDB"""
    tmdb_data = {
        "id": 1,
        "title": "TMDB",
        "genres": [{"name": "Action"}],
        "vote_average": 7.0,
        "vote_count": 100,
        "release_date": "2024-01-01",
    }
    credits = {"cast": [], "crew": []}

    context = build_film_context(tmdb_data=tmdb_data, credits=credits)

    assert context["source"] == "tmdb"
    assert context["title"] == "TMDB"


def test_build_film_not_bd_not_context_tmdb():
    """Если фильм не в БД и не передаюься нужные данные, возвращается None"""
    tmdb_data = {
        "id": 1,
        "title": "TMDB",
        "genres": [{"name": "Action"}],
        "vote_average": 7.0,
        "vote_count": 100,
        "release_date": "2024-01-01",
    }
    credits = None

    context = build_film_context(tmdb_data=tmdb_data, credits=credits)

    assert context is None
