from django.urls import reverse

import pytest

from films.models import UserFilm
from reviews.models import Review


@pytest.mark.django_db
class TestFilmViewsCatalog:
    def test_film_detail_view(self, client, user, film):
        """GET /film_detail/ - полная информация о фильме"""
        client.force_login(user)
        UserFilm.objects.create(user=user, film=film)
        url = reverse("films:film_detail", kwargs={"tmdb_id": film.tmdb_id})
        response = client.get(url)

        assert response.status_code == 200
        assert film.title in response.content.decode()

    def test_film_detail_view_unauth(self, client, film):
        """GET /films/123/ - аноним"""
        url = reverse("films:film_detail", kwargs={"tmdb_id": film.tmdb_id})
        response = client.get(url)

        assert response.status_code == 302

    def test_film_detail_from_db(self, client, user, film):
        """GET /films/123/ из БД"""
        client.force_login(user)
        url = reverse("films:film_detail", kwargs={"tmdb_id": film.tmdb_id})
        response = client.get(url)

        assert response.status_code == 200
        assert response.context["film"]["title"] == film.title
        assert response.context["film"]["in_library"] is False

    def test_film_detail_with_review(self, client, user, film, monkeypatch):
        """GET /films/123/ с отзывом"""
        client.force_login(user)
        UserFilm.objects.create(user=user, film=film)
        monkeypatch.setattr("reviews.models.Review.calculate_rating", lambda self: 8.0)
        Review.objects.create(
            user=user,
            film=film,
            plot_rating=8.0,
            acting_rating=8.0,
            directing_rating=8.0,
            visuals_rating=8.0,
            soundtrack_rating=8.0,
            watched_at="2026-01-11",
        )
        response = client.get(reverse("films:film_detail", kwargs={"tmdb_id": film.tmdb_id}))

        film_ctx = response.context["film"]
        assert film_ctx["has_review"] is True
        assert film_ctx["user_rating"] == 8.0

    def test_film_search_view(self, client, user):
        """GET /search/ - поисковый запрос фильма"""
        client.force_login(user)
        response = client.get(reverse("films:film_search"), {"q": "test"})

        assert response.status_code == 200
        assert "page_obj" in response.context

    def test_film_search_tmdb(self, client, user, monkeypatch):
        """GET /search/ - поисковый запрос фильма из TMDB"""
        client.force_login(user)
        monkeypatch.setattr("films.views.catalog.search_films", lambda **kwargs: ["film1", "film2"])
        response = client.get(reverse("films:film_search"), {"q": "test"})

        assert response.status_code == 200
        assert response.context["is_user_films"] is False
