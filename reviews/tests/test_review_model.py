import pytest


@pytest.mark.django_db
def test_review_calculate_rating(review):
    """Средняя оценка считается как среднее 5 критериев"""
    review.plot_rating = 6
    review.acting_rating = 8
    review.directing_rating = 10
    review.visuals_rating = 6
    review.soundtrack_rating = 10

    assert review.calculate_rating() == 8.0


@pytest.mark.django_db
def test_review_save_sets_user_rating(review):
    """При сохранении user_rating пересчитывается автоматически"""
    review.plot_rating = 10
    review.acting_rating = 10
    review.directing_rating = 10
    review.visuals_rating = 10
    review.soundtrack_rating = 10

    review.save()
    review.refresh_from_db()

    assert review.user_rating == 10


@pytest.mark.django_db
def test_review_str(review):
    """Строковое представление содержит пользователя, фильм и рейтинг"""
    result = str(review)

    assert review.user.username in result
    assert review.film.title in result
