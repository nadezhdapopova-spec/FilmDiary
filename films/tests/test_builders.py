import pytest

from films.services.builders import build_film_card, build_recommendation_cards, build_tmdb_collection_cards


@pytest.mark.django_db
def test_build_film_card_from_db(film, user, user_film, monkeypatch):
    """Проверяет формирование единого формата карточки фильма, если фильм в БД"""
    monkeypatch.setattr("films.services.user_film_services.get_user_film", lambda user, film: user_film)
    card = build_film_card(film=film, user=user)

    assert card["tmdb_id"] == film.tmdb_id
    assert card["in_library"] is True
    assert card["title"] == film.title


def test_build_film_card_from_tmdb():
    """Проверяет формирование единого формата карточки фильма, загруженного из TMDB"""
    tmdb_item = {
        "id": 1,
        "title": "TMDB film",
        "genre_ids": [1],
        "vote_average": 6.5,
    }
    genre_map = {1: "Action"}
    card = build_film_card(tmdb_item=tmdb_item, genre_map=genre_map)

    assert card["title"] == "TMDB film"
    assert card["genres"] == "Action"
    assert card["in_library"] is False


def test_build_film_card_invalid():
    """Проверяет вызов исключения ValueError в случае отсутствия данных"""
    with pytest.raises(ValueError):
        build_film_card()


@pytest.mark.django_db
def test_build_tmdb_collection_cards_existing_film(film, user):
    """Проверяет формирование карточки фильма из тематических подборок TMDB"""
    films = [{"id": film.tmdb_id, "genre_ids": []}]
    cards = build_tmdb_collection_cards(films, user=user)

    assert len(cards) == 1
    assert cards[0]["tmdb_id"] == film.tmdb_id


def test_build_tmdb_collection_cards_not_existing_film(user):
    """Проверяет, что для пустого id фильма не формируется карточка"""
    films = [{"id": None, "genre_ids": []}]
    cards = build_tmdb_collection_cards(films, user=user)
    assert len(cards) == 0


@pytest.mark.django_db
def test_build_recommendation_cards_from_db(user, film, monkeypatch):
    """Проверяет формирование карточки фильма для ежедневных персональных рекомендаций"""
    monkeypatch.setattr(
        "films.services.builders.get_user_recommendations", lambda user, limit=None: [{"tmdb_id": film.tmdb_id}]
    )
    cards = build_recommendation_cards(user)

    assert len(cards) == 1
    assert cards[0]["tmdb_id"] == film.tmdb_id
