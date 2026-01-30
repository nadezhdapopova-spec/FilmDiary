from films.models import UserFilm, Genre
from films.services.user_film_services import map_status
from reviews.models import Review
from services.tmdb import Tmdb


tmdb = Tmdb()


def search_tmdb_film(query: str, user, page_num: int=1) -> list[dict]:
    """Поиск по фильмам TMDB: возвращает список словарей для отображения фильмов (словарь=фильм)"""
    if not query:
        return []

    data = tmdb.search_movie(query=query, page=page_num)
    results = data.get("results", [])  or []
    if not results:
        return []

    ids = [item.get("id") for item in results if item.get("id")]

    user_films = (UserFilm.objects.select_related("film").filter(user=user, film__tmdb_id__in=ids))
    user_films_map = {uf.film.tmdb_id: uf for uf in user_films}
    existing = set(user_films_map.keys())  # получаем ВСЕ фильмы пользователя одним запросом

    all_genre_ids = set(
        g_id
        for item in results
        for g_id in item.get("genre_ids", [])
    )
    genres_qs = Genre.objects.filter(tmdb_id__in=all_genre_ids)  # формируем один раз для запроса
    genre_map = {g.tmdb_id: g.name for g in genres_qs}

    reviews_map = {
        r.film.tmdb_id: r
        for r in Review.objects.filter(
            user=user,
            film__tmdb_id__in=ids
        )
    }

    films: list[dict] = []
    for item in results:
        tmdb_id = item.get("id")
        user_film = user_films_map.get(tmdb_id)
        genre_ids = item.get("genre_ids", []) or []
        film_genres = [genre_map[g_id] for g_id in genre_ids[:2] if g_id in genre_map]
        poster_path = item.get("poster_path")
        poster_url = None
        if poster_path:
            if not poster_path.endswith(('.jpg', '.jpeg')):
                poster_path += '.jpg'
            poster_url = f"https://image.tmdb.org/t/p/w342{poster_path}"

        film_dict = {
                "tmdb_id": item.get("id"),
                "title": item.get("title") or item.get("name", "Без названия"),
                "poster_url": poster_url,
                "release_date": item.get("release_date", "")[:4] or "----",

                "genres": ", ".join(film_genres) if film_genres else "",
                "tmdb_rating": round(float(item.get("vote_average", 0)), 1),
                "in_library": tmdb_id in existing,
            }
        has_review = tmdb_id in reviews_map
        review = reviews_map.get(tmdb_id)
        rating = review.user_rating if review else None

        film_dict.update(map_status(user_film, has_review, rating))  # получаем и добавляем пользовательский статус фильма
        films.append(film_dict)
    films.sort(key=lambda f: f["tmdb_rating"], reverse=True)

    return films


def search_user_film(query: str, user, page_num: int = 1) -> list[UserFilm]:
    """Поиск по фильмам пользователя из БД"""
    films_qs = (UserFilm.objects.filter(
        user=user,
        film__title__icontains=query
    ).select_related("film").prefetch_related("film__genres", "film__actors", "film__crew").order_by("-created_at"))

    return list(films_qs[(page_num - 1) * 12: page_num * 12])


def search_favorite_films(query: str, user, page_num: int = 1) -> list[UserFilm]:
    """Поиск только по любимым фильмам пользователя"""
    films_qs = UserFilm.objects.filter(
        user=user,
        is_favorite=True,
        film__title__icontains=query
    ).select_related("film").prefetch_related("film__genres", "film__actors", "film__crew").order_by("-created_at")

    return list(films_qs[(page_num - 1) * 12: page_num * 12])


def search_watched_films(query: str, user, page_num: int = 1) -> list[Review]:
    """Поиск только по просмотренным фильмам пользователя"""
    films_qs = Review.objects.filter(
        user=user,
        film__title__icontains=query
    ).select_related("film").prefetch_related("film__genres", "film__actors", "film__crew").order_by("-created_at")

    return list(films_qs[(page_num - 1) * 12: page_num * 12])


def search_reviewed_films(query: str, user, page_num: int = 1) -> list[Review]:
    """Поиск только по фильмам c отзывами"""
    qs = (Review.objects.filter(
        user=user,
        film__title__icontains=query
    ).exclude(review__isnull=True).exclude(review="")
               .select_related("film").prefetch_related("film__genres", "film__actors", "film__crew")
               .order_by("-created_at"))

    return list(qs[(page_num - 1) * 12: page_num * 12])


def search_films(query: str, user, page_num: int=1, source: str = 'tmdb') -> list:
    """
    Поиск фильмов: "tmdb_film" — глобальный поиск по TMDB,
                   "user_film" — поиск по фильмам пользователя из БД
    """
    if not query:
        return []

    if source == "user_films":
        return search_user_film(query, user, page_num)  # list[Film]
    elif source == "favorites":
        return search_favorite_films(query, user, page_num)
    elif source == "watched":
        return search_watched_films(query, user, page_num)
    elif source == "reviewed":
        return search_reviewed_films(query, user, page_num)
    else:
        return search_tmdb_film(query, user, page_num)  # list[dict] для TMDB
