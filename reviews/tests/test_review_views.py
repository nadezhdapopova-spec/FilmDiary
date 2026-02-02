from django.urls import reverse

import pytest


@pytest.mark.django_db
def test_review_detail_owner(client, user, review):
    """Автор может открыть карточку отзыва"""
    client.force_login(user)

    url = reverse("reviews:review_detail", args=[review.pk])
    response = client.get(url)

    assert response.status_code == 200


@pytest.mark.django_db
def test_review_detail_forbidden(client, other_user, review):
    """Посторонний пользователь получает 404"""
    client.force_login(other_user)

    url = reverse("reviews:review_detail", args=[review.pk])
    response = client.get(url)

    assert response.status_code == 404
