from datetime import date

import pytest

from films.models import Film
from reviews.models import Review
from users.models import CustomUser


@pytest.fixture
def user(db):
    return CustomUser.objects.create_user(username="test", password="123")


@pytest.fixture
def other_user(db):
    return CustomUser.objects.create_user(username="test2", email="test2@test.ru", password="54321")


@pytest.fixture
def film(db):
    """Фильм для тестов отзывов"""
    return Film.objects.create(
        tmdb_id=1,
        title="Test Film",
    )


@pytest.fixture
def review(db, user, film):
    """Отзыв пользователя на фильм"""
    return Review.objects.create(
        user=user,
        film=film,
        watched_at=date(2024, 1, 1),
        plot_rating=7,
        acting_rating=7,
        directing_rating=7,
        visuals_rating=7,
        soundtrack_rating=7,
        user_rating=7,
        review="Хороший фильм",
    )
