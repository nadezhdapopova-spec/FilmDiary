from datetime import date

from django.contrib.auth.models import Group

import pytest

from films.models import Film, Genre
from reviews.models import Review
from users.models import CustomUser


@pytest.fixture
def user(db):
    return CustomUser.objects.create_user(username="test", password="123")


@pytest.fixture
def admin_user(db):
    return CustomUser.objects.create_superuser(username="test1", email="test@test.ru", password="12345")


@pytest.fixture
def other_user(db):
    return CustomUser.objects.create_user(username="test2", email="test2@test.ru", password="54321")


@pytest.fixture
def manager_user(db):
    manager_user = CustomUser.objects.create_user(
        username="test3", email="test3@test.ru", password="543456", is_staff=True
    )
    group, _ = Group.objects.get_or_create(name="Manager")
    manager_user.groups.add(group)
    return manager_user


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
def review(db, film, user):
    return Review.objects.create(
        user=user,
        film=film,
        user_rating=8.0,
        watched_at="2024-01-01",
        plot_rating=8.0,
        acting_rating=8.0,
        directing_rating=8.0,
        visuals_rating=8.0,
        soundtrack_rating=8.0,
    )


@pytest.fixture
def anon_user():
    class Anon:
        is_authenticated = False

    return Anon()
