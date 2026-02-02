from datetime import date
from unittest.mock import Mock, patch

import pytest

from films.models import Film, Genre, UserFilm
from users.models import CustomUser


@pytest.fixture
def user(db):
    return CustomUser.objects.create_user(username="test", password="123")


@pytest.fixture
def anon_user():
    class Anon:
        is_authenticated = False

    return Anon()


@pytest.fixture
def genre(db):
    return Genre.objects.create(tmdb_id=1, name="Action")


@pytest.fixture
def film(db, genre):
    film = Film.objects.create(
        tmdb_id=100,
        title="Test film",
        vote_average=7.8,
        release_date=date(2024, 1, 1),
    )
    film.genres.add(genre)
    return film


@pytest.fixture
def user_film(db, user, film):
    return UserFilm.objects.create(user=user, film=film, is_favorite=True)


@pytest.fixture
def celery_eager(monkeypatch):
    """Включение eager режима для Celery"""
    monkeypatch.setattr("celery.current_app.conf.task_always_eager", True)
    monkeypatch.setattr("celery.current_app.conf.task_eager_propagates", True)
    yield
    monkeypatch.setattr("celery.current_app.conf.task_always_eager", False)
    monkeypatch.setattr("celery.current_app.conf.task_eager_propagates", False)


@pytest.fixture
def mock_logger():
    """Мок логгера"""
    with patch("films.tasks.logger") as mock_log:
        yield mock_log


@pytest.fixture
def mock_cache():
    """Мок для Redis кеша"""
    mock_cache = Mock()
    mock_cache.set.return_value = True
    with patch("films.tasks.cache", mock_cache):
        yield mock_cache


@pytest.fixture
def mock_tmdb():
    """Мок TMDB API"""
    mock_tmdb = Mock()
    mock_tmdb.build_recommendations.return_value = ["rec1", "rec2"]
    with patch("films.tasks.Tmdb", return_value=mock_tmdb):
        yield mock_tmdb


@pytest.fixture
def mock_build_recommendations():
    """Мок для build_recommendations"""
    mock_rec = Mock(return_value=[{"movie_id": 1, "score": 0.9, "reasons": ["test"]}])
    with patch("services.recommendations.build_recommendations", mock_rec):
        yield mock_rec


@pytest.fixture
def django_db_setup():
    """Обеспечивает django_db для всех тестов"""
    pass


@pytest.fixture
def tmdb_payload():
    return {
        "details": {
            "title": "Test Film",
            "genres": [{"id": 1, "name": "Action"}],
            "release_date": date(2024, 1, 1),
        },
        "credits": {
            "cast": [
                {"id": 10, "name": "Actor 1", "character": "Hero"},
            ],
            "crew": [
                {"id": 20, "name": "Director 1", "job": "Director"},
            ],
        },
    }
