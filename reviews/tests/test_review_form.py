import pytest
from reviews.forms import ReviewForm


@pytest.mark.django_db
def test_review_form_valid():
    """Форма валидна при корректных данных"""
    form = ReviewForm(data={
        "watched_at": "2024-01-01",
        "number_of_views": 3,
        "plot_rating": 8,
        "acting_rating": 8,
        "directing_rating": 8,
        "visuals_rating": 8,
        "soundtrack_rating": 8,
        "review": "Отличный фильм",
    })

    assert form.is_valid()


@pytest.mark.django_db
def test_review_form_watched_at_required():
    """Дата просмотра обязательна"""
    form = ReviewForm(data={})

    assert not form.is_valid()
    assert "watched_at" in form.errors


@pytest.mark.django_db
def test_review_form_initial_date(review):
    """Дата просмотра приводится к ISO-формату в initial"""
    form = ReviewForm(instance=review)

    assert form.initial["watched_at"] == review.watched_at.strftime("%Y-%m-%d")
