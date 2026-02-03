from films.models import Film, Genre
from films.services.tmdb_movie_payload import get_tmdb_movie_payload
from films.services.user_film_services import get_user_film, get_user_recommendations, map_status
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
        genres_str = ", ".join(g.name for g in film.genres.all()[:2]) or "—"
        return {
            "tmdb_id": int(film.tmdb_id) if film.tmdb_id is not None else None,
            "title": film.title,
            "poster_url": build_poster_url(film.poster_path),
            "release_date": film.release_date.year if film.release_date else "—",
            "genres": genres_str,
            "rating": round(film.vote_average, 1) if film.vote_average else None,
            "in_library": bool(user_film),
            "is_tmdb_dict": False,
            **map_status(
                user_film=user_film,
                has_review=False,
                rating=None,
            ),
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
            "is_tmdb_dict": True,
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

    all_genre_ids = {g for f in films for g in f.get("genre_ids", [])}
    genres = Genre.objects.filter(tmdb_id__in=all_genre_ids)
    genre_map = {g.tmdb_id: g.name for g in genres}

    tmdb_ids = [f["id"] for f in films if f.get("id")]
    films_qs = Film.objects.filter(tmdb_id__in=tmdb_ids).prefetch_related("genres")
    films_list = list(films_qs)
    existing_films = {f.tmdb_id: f for f in films_list}

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
    tmdb_ids = [r["tmdb_id"] for r in recs]
    films_qs = Film.objects.filter(tmdb_id__in=tmdb_ids).prefetch_related("genres")
    films_list = list(films_qs)
    films_map = {f.tmdb_id: f for f in films_list}  # {603: <Film: The Matrix>, 550: <Film: Fight Club>,..}

    for rec in recs:
        tmdb_id = rec["tmdb_id"]
        film = films_map.get(tmdb_id)

        if film:
            cards.append(build_film_card(film=film, user=user))
            continue

        payload = get_tmdb_movie_payload(tmdb_id)
        if payload:
            details = payload["details"]
            cards.append(
                build_film_card(
                    tmdb_item={**details, "genre_ids": [g["id"] for g in details.get("genres", [])]},
                    genre_map={g["id"]: g["name"] for g in details.get("genres", [])},
                    user=user,
                )
            )

    return cards
