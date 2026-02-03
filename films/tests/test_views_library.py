from django.urls import reverse

import pytest

from films.models import UserFilm


@pytest.mark.django_db
class TestFilmViewsCatalog:
    def test_home_view_anon(self, client):
        """Вход на главную страницу неавторизованного пользователя: успешно"""
        response = client.get(reverse("films:home"))

        assert response.status_code == 200
        assert response.context["home_page"] is True

    def test_home_view_auth(self, client, user, monkeypatch):
        """Вход на главную страницу авторизованного пользователя: успешно"""
        client.force_login(user)
        monkeypatch.setattr("films.views.library.build_recommendation_cards", lambda u, limit: ["rec1"])
        response = client.get(reverse("films:home"))

        assert "recs_for_me" in response.context
        assert "recent_watched" in response.context

    def test_recommends_personal(self, client, user, monkeypatch):
        """Вывод на главной странице ежедневных рекомендаций для авторизованного пользователя: успешно"""
        client.force_login(user)
        monkeypatch.setattr("films.views.library.build_recommendation_cards", lambda u, limit: ["film"])
        response = client.get(reverse("films:recommends"), {"type": "recommended"})

        assert response.context["recommend_type"] == "recommended"
        assert response.context["films"] == ["film"]

    def test_recommends_popular(self, client, user, monkeypatch):
        """Вывод фильмов TMDB из подборки 'Популярные фильмы' для авторизованного пользователя"""
        client.force_login(user)

        class FakeTmdb:
            def get_popular(self, pages):
                return [{"id": 1}]

        monkeypatch.setattr("films.views.library.Tmdb", lambda: FakeTmdb())
        monkeypatch.setattr("films.views.library.build_tmdb_collection_cards", lambda films, user=None: films)
        response = client.get(reverse("films:recommends"), {"type": "popular"})

        assert response.context["recommend_title"] == "Популярные фильмы"

    def test_my_films_view(self, client, user, film):
        """Вывод фильмов авторизованного пользователя"""
        client.force_login(user)
        UserFilm.objects.create(user=user, film=film)
        response = client.get(reverse("films:my_films"))

        assert response.status_code == 200
        assert len(response.context["items"]) == 1

    def test_favorite_films_view(self, client, user, film):
        """Вывод любимых фильмов авторизованного пользователя"""
        client.force_login(user)
        UserFilm.objects.create(user=user, film=film, is_favorite=True)
        response = client.get(reverse("films:favorite_films"))

        assert response.context["favorites_page"] is True

    def test_add_film_no_tmdb(self, client, user):
        """Добавление фильма в свою коллекцию, если отсутствует tmdb_id: неуспешно"""
        client.force_login(user)
        response = client.post(reverse("films:add_film"), {})

        assert response.status_code == 400

    def test_add_film_success(self, client, user, film, monkeypatch):
        """Добавление авторизованным пользователем фильма в свою коллекцию: успешно"""
        client.force_login(user)
        monkeypatch.setattr(
            "films.views.library.save_film_from_tmdb", lambda **kw: (film, False, UserFilm(user=user, film=film), True)
        )

        response = client.post(reverse("films:add_film"), {"tmdb_id": film.tmdb_id})
        assert response.json()["status"] == "added"

    def test_update_film_favorite(self, client, user, film):
        """Обновление своего фильма авторизованным пользователем, добавление в любимое: успешно"""
        client.force_login(user)
        UserFilm.objects.create(user=user, film=film)
        response = client.post(reverse("films:update_status"), {"tmdb_id": film.tmdb_id, "action": "favorite"})

        assert response.json()["is_favorite"] is True

    def test_delete_film(self, client, user, film):
        """Удаление своего фильма авторизованным пользователем: успешно"""
        client.force_login(user)
        UserFilm.objects.create(user=user, film=film)
        films_amount = UserFilm.objects.count()
        response = client.post(reverse("films:delete_film", kwargs={"tmdb_id": film.tmdb_id}))

        assert response.status_code == 302
        assert UserFilm.objects.count() == films_amount - 1

    def test_custom_404(self, client):
        """Проверка на вывод исключения"""
        response = client.get("/not-exists/")
        assert response.status_code == 404
