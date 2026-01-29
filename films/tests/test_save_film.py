import pytest

from films.models import UserFilm
from films.services.save_film import save_film_from_tmdb


def test_film_exists_returns_film(film, user):
    """Если фильм существует - возвращает его"""
    result = save_film_from_tmdb(tmdb_id=film.tmdb_id, user=user)
    assert len(result) == 4
    assert result[0] == film
    assert result[1] is False

@pytest.mark.django_db
def test_no_payload_returns_none(monkeypatch, user):
    """Нет payload - возвращает (None, False)"""
    monkeypatch.setattr("films.services.tmdb_movie_payload.get_tmdb_movie_payload", lambda tid: None)
    result = save_film_from_tmdb(tmdb_id=999, user=user)
    assert result == (None, False)

@pytest.mark.django_db
def test_create_user_film(film, user):
    """Создает UserFilm для существующего фильма"""
    assert not UserFilm.objects.filter(user=user, film=film).exists()

    result = save_film_from_tmdb(tmdb_id=film.tmdb_id, user=user)
    film_result, created_film, user_film, created_uf = result

    assert UserFilm.objects.filter(user=user, film=film).exists()
    assert created_uf is True


@pytest.mark.django_db
def test_save_film_from_tmdb_exists(monkeypatch, film, user):
    """Тест существующего фильма"""
    monkeypatch.setattr("films.services.tmdb_movie_payload.get_tmdb_movie_payload", lambda tid: None)

    result_film, created, user_film, created_uf = save_film_from_tmdb(tmdb_id=film.tmdb_id, user=user)

    assert result_film == film
    assert created is False
