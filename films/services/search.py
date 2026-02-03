from django.utils import timezone

from calendar_events.models import CalendarEvent
from films.models import Genre, UserFilm
from reviews.models import Review
from services.tmdb import Tmdb

tmdb = Tmdb()


def search_tmdb_film(query: str, user, page_num: int = 1) -> list[dict]:
    """Поиск по фильмам TMDB: возвращает список словарей для отображения фильмов (словарь=фильм)"""
    if not query:
        return []

    data = tmdb.search_movie(query=query, page=page_num)
    results = data.get("results", []) or []
    if not results:
        return []

    ids = [item.get("id") for item in results if item.get("id")]
    user_films_map = {}
    reviews_map = {}
    planned_ids = set()
    if user:
        user_films = UserFilm.objects.select_related("film").filter(user=user, film__tmdb_id__in=ids)
        user_films_map = {uf.film.tmdb_id: uf for uf in user_films}
        reviews = Review.objects.filter(user=user, film__tmdb_id__in=ids)
        reviews_map = {r.film.tmdb_id: r for r in reviews}
        planned_ids = set(
            CalendarEvent.objects.filter(
                user=user,
                film__tmdb_id__in=ids,
                planned_date__gte=timezone.now().date()
            ).values_list("film__tmdb_id", flat=True)
        )
    all_genre_ids = set(
        g_id
        for item in results
        for g_id in item.get("genre_ids", [])
    )
    genre_map = {}
    if all_genre_ids:
        genres_qs = Genre.objects.filter(tmdb_id__in=all_genre_ids)
        genre_map = {g.tmdb_id: g.name for g in genres_qs}

    items = []
    for item in results:
        tmdb_id = item["id"]
        genre_ids = item.get("genre_ids", []) or []
        film_genres = [genre_map[g_id] for g_id in genre_ids[:2] if g_id in genre_map]
        user_film = user_films_map.get(tmdb_id)
        is_favorite = user_film.is_favorite if user_film else False
        film_dict = {
            "tmdb_id": tmdb_id,
            "title": item.get("title") or item.get("name", "Без названия"),
            "poster_url": (
                f"https://image.tmdb.org/t/p/w342{item['poster_path']}"
                if item.get("poster_path")
                else None
            ),
            "poster_path": item.get("poster_path"),
            "release_date": item.get("release_date", "")[:4] or "-",
            "genres": ", ".join(film_genres) if film_genres else "",
            "has_review": tmdb_id in reviews_map,
            "in_library": tmdb_id in user_films_map,
            "is_favorite": is_favorite,
            "is_tmdb_dict": True,
        }
        items.append({
            "film": film_dict,
            "user_film": user_films_map.get(tmdb_id),
            "review": reviews_map.get(tmdb_id),
            "is_planned": tmdb_id in planned_ids,
        })

    return items


def get_film_statuses(user, film_ids):
    """
    Вспомогательная функция для получения статусов:
    возвращает reviews_map (id фильма: отзыв), planned_ids(id запланированных фильмов)
    """
    if not film_ids:
        return {}, set()

    reviews_qs = Review.objects.filter(user=user, film_id__in=film_ids)
    reviews_map = {r.film_id: r for r in reviews_qs}

    planned_qs = CalendarEvent.objects.filter(
        user=user, film_id__in=film_ids, planned_date__gte=timezone.now().date()
    )
    planned_ids = set(planned_qs.values_list("film_id", flat=True))

    return reviews_map, planned_ids


def search_user_film(query: str, user):
    """Поиск по фильмам пользователя из БД"""
    qs = (
        UserFilm.objects.filter(user=user)
        .select_related("film")
        .prefetch_related("film__genres")
        .order_by("-created_at")
    )
    if query:
        qs = qs.filter(film__title__icontains=query)
    films = list(qs)
    film_ids = [uf.film_id for uf in films]
    reviews_map, planned_ids = get_film_statuses(user, film_ids)
    return [
        {
            "user_film": uf,
            "film": uf.film,
            "review": reviews_map.get(uf.film_id),
            "is_planned": uf.film_id in planned_ids,
            "is_favorite": uf.is_favorite,
        }
        for uf in films
    ]


def search_favorite_films(query: str, user):
    """Поиск только по любимым фильмам пользователя"""
    qs = (
        UserFilm.objects.filter(user=user, is_favorite=True)
        .select_related("film")
        .prefetch_related("film__genres")
        .order_by("-created_at")
    )
    if query:
        qs = qs.filter(film__title__icontains=query)
    films = list(qs)
    film_ids = [uf.film_id for uf in films]
    reviews_map, planned_ids = get_film_statuses(user, film_ids)
    return [
        {
            "user_film": uf,
            "film": uf.film,
            "review": reviews_map.get(uf.film_id),
            "is_planned": uf.film_id in planned_ids,
            "is_favorite": uf.is_favorite,
        }
        for uf in films
    ]


def search_watched_films(query: str, user):
    """Поиск только по просмотренным фильмам пользователя"""
    qs = Review.objects.filter(user=user).select_related("film")
    if query:
        qs = qs.filter(film__title__icontains=query)
    reviews = list(qs)
    if not reviews:
        return []
    film_ids = [r.film_id for r in reviews]
    user_map = {
        uf.film_id: uf
        for uf in UserFilm.objects.filter(user=user, film_id__in=film_ids)
    }
    reviews_map, planned_ids = get_film_statuses(user, film_ids)
    items = [
        {
            "film": r.film,
            "user_film": user_map.get(r.film_id),
            "review": r,
            "is_planned": r.film_id in planned_ids,
        }
        for r in reviews
    ]
    for item in items:   # добавляем is_favorite к каждому review
        item["review"].is_favorite = bool(item["user_film"] and item["user_film"].is_favorite)

    return items


def search_reviewed_films(query: str, user):
    """Поиск только по фильмам c отзывами"""
    qs = Review.objects.filter(user=user).exclude(review__isnull=True).exclude(review="").select_related("film")
    if query:
        qs = qs.filter(film__title__icontains=query)
    reviews = list(qs)
    film_ids = [r.film_id for r in reviews]
    user_map = {
        uf.film_id: uf
        for uf in UserFilm.objects.filter(user=user, film_id__in=film_ids)
    }
    reviews_map, planned_ids = get_film_statuses(user, film_ids)
    items = [
        {
            "film": r.film,
            "user_film": user_map.get(r.film_id),
            "review": r,
            "is_planned": r.film_id in planned_ids,
        }
        for r in reviews
    ]
    for item in items:  # добавляем is_favorite к каждому review
        item["review"].is_favorite = bool(item["user_film"] and item["user_film"].is_favorite)
    return items


def search_films(query: str, user, page_num: int = 1, source: str = "tmdb"):
    """
    Поиск фильмов: "tmdb_film" — глобальный поиск по TMDB,
                   "user_film" — поиск по фильмам пользователя из БД
    """
    if source == "tmdb":
        return search_tmdb_film(query, user, page_num)
    if not user or not user.is_authenticated:
        return []
    if source == "user_films":
        return search_user_film(query, user)
    if source == "favorites":
        return search_favorite_films(query, user)
    if source == "watched":
        return search_watched_films(query, user)
    if source == "reviewed":
        return search_reviewed_films(query, user)
    return []
