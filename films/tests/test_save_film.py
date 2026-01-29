from unittest.mock import Mock

import pytest

from films.models import UserFilm, Film
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
    monkeypatch.setattr("films.services.save_film.get_tmdb_movie_payload", lambda tid: None)
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
    monkeypatch.setattr("films.services.save_film.get_tmdb_movie_payload", lambda tid: None)

    result_film, created, user_film, created_uf = save_film_from_tmdb(tmdb_id=film.tmdb_id, user=user)

    assert result_film == film
    assert created is False

@pytest.mark.django_db
def test_save_film_existing_film(user, film, monkeypatch):
    """Если фильм есть в БД"""
    monkeypatch.setattr("films.services.save_film.get_tmdb_movie_payload", Mock())

    film2, created_film, user_film, created_user_film = save_film_from_tmdb(
        tmdb_id=film.tmdb_id,
        user=user,
    )

    assert film2 == film
    assert created_film is False
    assert created_user_film is True

@pytest.mark.django_db
def test_save_film_from_tmdb_creates_all(user, tmdb_payload, monkeypatch):
    """Если фильм сохраняется из TMDB"""
    monkeypatch.setattr(
        "films.services.save_film.get_tmdb_movie_payload",
        Mock(return_value=tmdb_payload),
    )
    films_amount = Film.objects.count()

    film, created_film, user_film, created_user_film = save_film_from_tmdb(tmdb_id=999, user=user)

    assert created_film is True
    assert created_user_film is True
    assert Film.objects.count() == films_amount + 1

@pytest.mark.django_db
def test_save_film_tmdb_fail_rollback(user, monkeypatch):
    """Если TMDB вернул None: rollback"""
    monkeypatch.setattr(
        "films.services.save_film.get_tmdb_movie_payload",
        Mock(return_value=None)
    )
    films_amount = Film.objects.count()
    user_films_amount = UserFilm.objects.count()
    result = save_film_from_tmdb(tmdb_id=123, user=user)

    assert result == (None, False)
    assert Film.objects.count() == films_amount
    assert UserFilm.objects.count() == user_films_amount

@pytest.mark.django_db
def test_save_film_user_film_exists(user, film, monkeypatch):
    UserFilm.objects.create(user=user, film=film)
    monkeypatch.setattr("films.services.save_film.get_tmdb_movie_payload",Mock())

    _, _, _, created_user_film = save_film_from_tmdb(tmdb_id=film.tmdb_id, user=user)

    assert created_user_film is False
