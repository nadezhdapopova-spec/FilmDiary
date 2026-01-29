from datetime import date

import pytest

from films.models import Genre, Film, UserFilm
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
