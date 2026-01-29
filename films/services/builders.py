from films.models import Film, Genre
from films.services.tmdb_movie_payload import get_tmdb_movie_payload
from films.services.user_film_services import get_user_film, map_status, get_user_recommendations
from films.services.utils import build_poster_url, extract_year, join_genres


def build_film_card(
    *,
    film: Film | None = None,
    tmdb_item: dict | None = None,
    genre_map: dict | None = None,
    user=None,
) -> dict:
    """Возвращает единый формат карточки фильма для film_preview_card.html из БД и из TMDB"""
    if film:
        user_film = get_user_film(user, film) if user else None

        return {
            "tmdb_id": film.tmdb_id,
            "title": film.title,
            "poster_url": build_poster_url(film.poster_path),
            "release_date": film.release_date.year if film.release_date else "—",
            "genres": ", ".join(g.name for g in film.genres.all()[:2]),
            "rating": round(film.vote_average, 1) if film.vote_average else None,
            "in_library": bool(user_film),
            **map_status(user_film=user_film, has_review=False, rating=None,),
        }

    if tmdb_item:
        return {
            "tmdb_id": tmdb_item["id"],
            "title": tmdb_item.get("title") or tmdb_item.get("name", "Без названия"),
            "poster_url": build_poster_url(tmdb_item.get("poster_path")),
            "release_date": extract_year(tmdb_item.get("release_date")),
            "genres": join_genres(tmdb_item.get("genre_ids"), genre_map),
            "rating": round(tmdb_item.get("vote_average", 0), 1),
            "in_library": False,
            "is_favorite": False,
            "has_review": False,
            "user_rating": None,
            "rating_color": None,
        }

    raise ValueError("build_film_card: film or tmdb_item required")


def build_tmdb_collection_cards(films, user=None):
    """Возвращает единый формат карточки фильма из тематических подборок TMDB"""
    if not films:
        return []

    all_genre_ids = {
        g for f in films for g in f.get("genre_ids", [])
    }
    genres = Genre.objects.filter(tmdb_id__in=all_genre_ids)
    genre_map = {g.tmdb_id: g.name for g in genres}

    existing_films = {
        f.tmdb_id: f
        for f in Film.objects.filter(
            tmdb_id__in=[f["id"] for f in films if f.get("id")]
        ).prefetch_related("genres")
    }

    cards = []

    for item in films:
        tmdb_id = item.get("id")
        if not tmdb_id:
            continue

        if tmdb_id in existing_films:
            cards.append(
                build_film_card(
                    film=existing_films[tmdb_id],
                    user=user,
                )
            )
        else:
            cards.append(
                build_film_card(
                    tmdb_item=item,
                    genre_map=genre_map,
                    user=user,
                )
            )

    return cards


def build_recommendation_cards(user, limit=4) -> list[dict]:
    """Возвращает единый формат карточки фильма для ежедневных персональных рекомендаций"""
    recs = get_user_recommendations(user, limit=limit)
    cards = []

    films_map = {
        f.tmdb_id: f
        for f in Film.objects.filter(
            tmdb_id__in=[r["tmdb_id"] for r in recs]
        ).prefetch_related("genres")
    }

    for rec in recs:
        tmdb_id = rec["tmdb_id"]
        film = films_map.get(tmdb_id)

        if film:
            cards.append(build_film_card(film=film, user=user))
            continue

        payload = get_tmdb_movie_payload(tmdb_id)
        if payload:
            cards.append(
                build_film_card(
                    tmdb_item=payload["details"],
                    genre_map={
                        g["id"]: g["name"]
                        for g in payload["details"].get("genres", [])
                    },
                    user=user,
                )
            )

    return cards
