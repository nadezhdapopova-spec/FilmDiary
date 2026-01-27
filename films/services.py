from datetime import datetime
from typing import Optional
from django.db import transaction

from django.core.cache import cache

from films.models import Film, Genre, Actor, FilmActor, Person, FilmCrew, UserFilm
from reviews.models import Review
from services.tmdb import Tmdb


tmdb = Tmdb()


def get_crew_by_job(film, job):
    """Возвращает данные из БД о создателе фильма по конкретной должности"""
    return [fc for fc in film.filmcrew_set.all() if fc.job == job]


def get_crew_member(credits, job):
    """Возвращает данные из API TMDB о создателе фильма по конкретной должности"""
    return next((p for p in credits.get("crew", []) if p.get("job") == job), None)


def get_user_film(user, film):
    """Возвращает фильм, если пользователь авторизован и у него есть данный фильм в коллекции"""
    if not user.is_authenticated:
        return None
    return UserFilm.objects.filter(user=user, film=film).first()


def get_user_recommendations(user, *, limit=None):
    """Берет вычесленные для пользователя рекомендации из кэша"""
    if not user.is_authenticated:
        return []
    recs = cache.get(f"recs:user:{user.id}", [])
    return recs[:limit] if limit else recs


def build_film_context(*, film=None, tmdb_data=None, credits=None):
    """Возвращает единый контекст для шаблона film_detail.html из БД или из API TMDB"""
    if film:
        return {
            "source": "db",
            "in_library": True,
            "tmdb_id": film.tmdb_id,

            "title": film.title,
            "original_title": film.original_title,
            "tagline": film.tagline,
            "overview": film.overview,
            "genres": [g.name for g in film.genres.all()],

            "poster_url": film.poster_path,
            "backdrop_url": film.backdrop_path,

            "actors": [
                {
                    "name": f_a.actor.name,
                    "character": f_a.character,
                    "photo": f_a.actor.profile_path,
                }
                for f_a in film.filmactor_set.select_related("actor").all()
            ],
            "director": [d.person.name for d in get_crew_by_job(film, "Director")],
            "writer": [w.person.name for w in get_crew_by_job(film, "Writer")],
            "composer": [c.person.name for c in get_crew_by_job(film, "Composer")],  # одного выбираем в шаблоне
            "producer": [p.person.name for p in get_crew_by_job(film, "Producer")],

            "original_country": film.original_country,
            "runtime": film.runtime,
            "release_date": f"{film.release_date.strftime("%d %m %Y")} г.",
            "release_year": film.release_date.year,

            "budget": format_nums(film.budget),
            "revenue": format_nums(film.revenue),
            "production_company": film.production_company,

            "rating": round(film.vote_average, 1),
            "vote_count": format_nums(film.vote_count)
        }

    if tmdb_data and credits:
        director = get_crew_member(credits, "Director")
        writer = get_crew_member(credits, "Writer")
        composer = get_crew_member(credits, "Composer")
        producer = get_crew_member(credits, "Producer")
        release_date_str = tmdb_data.get("release_date")
        if release_date_str:
            release = datetime.strptime(release_date_str, "%Y-%m-%d").date()
            release_date = release.strftime("%d %m %Y")
            release_year = release.year  # 2024
        else:
            release_date = "—"
            release_year = "—"

        return {
            "source": "tmdb",
            "in_library": False,
            "tmdb_id": tmdb_data["id"],

            "title": tmdb_data.get("title"),
            "original_title": tmdb_data.get("original_title"),
            "tagline": tmdb_data.get("tagline"),
            "overview": tmdb_data.get("overview"),
            "genres": [g.get("name") for g in tmdb_data.get("genres", [])],

            "poster_url": tmdb_data.get("poster_path"),
            "backdrop_url": tmdb_data.get("backdrop_path"),

            "actors": [
                {
                    "name": actor["name"],
                    "character": actor.get("character"),
                    "photo": actor.get("profile_path"),
                }
                for actor in credits.get("cast", [])[:10]
            ],
            "director": [director.get("name")] if director else [],
            "writer": [writer.get("name")] if writer else [],
            "composer": [composer.get("name")] if composer else [],
            "producer": [producer.get("name")] if producer else [],

            "original_country": (
                tmdb_data.get("origin_country")[0]
                if tmdb_data.get("origin_country")
                else None
            ),
            "runtime": tmdb_data.get("runtime"),
            "release_date": f"{release_date} г.",
            "release_year": release_year,
            "budget": format_nums(tmdb_data.get("budget")),
            "revenue": format_nums(tmdb_data.get("revenue")),
            "production_company": (
                tmdb_data["production_companies"][0]["name"]
                if tmdb_data.get("production_companies")
                else None
            ),

            "rating": round(tmdb_data.get("vote_average"), 1),
            "user_rating": None,
            "has_review": False,
            "is_favorite": False,
            "rating_color": None,
            "vote_count": format_nums(tmdb_data.get("vote_count"))
        }
    return None


def get_tmdb_movie_payload(tmdb_id: int) -> Optional[dict]:
    """Кэширует данные из TMDB, если их еще нет, или возвращает данные из кэша (TTL: 12 часов)"""
    cache_key = f"tmdb:movie:{tmdb_id}"

    data = cache.get(cache_key)
    if data:
        return data

    details = tmdb.get_movie_details(tmdb_id)
    credits = tmdb.get_credits(tmdb_id)
    if not details or not credits:
        print(f"TMDB API failed: details={details}, credits={credits}")
        return None
    data = {
        "details": details,
        "credits": credits,
    }
    cache.set(cache_key, data, timeout=60 * 60 * 12)  # 12 часов
    return data


@transaction.atomic
def save_film_from_tmdb(*, tmdb_id: int, user):
    """
    Создает и записывает объект фильма в БД, если еще не записан:
    если успешно - commit, если любая ошибка - rollback: или фильм сохранён в БД полностью, или не сохраняется вообще
    """
    film = Film.objects.filter(tmdb_id=tmdb_id).first()  # проверяем, есть ли уже фильм с БД фильмов
    created_film = False

    if not film:
        payload = get_tmdb_movie_payload(tmdb_id)  # получаем TMDB данные из кэша
        if not payload or "details" not in payload:
            return None, False

        details = payload["details"]
        credits = payload["credits"]

        film = Film.objects.create(  # создаем фильм
            tmdb_id=tmdb_id,
            title=details["title"],
            original_title=details.get("original_title"),
            tagline=details.get("tagline"),
            overview=details.get("overview", ""),
            runtime=details.get("runtime"),
            original_country=details.get("original_country"),
            release_date=details.get("release_date") or None,
            production_company=details.get("production_company"),
            poster_path=details.get("poster_path"),
            backdrop_path=details.get("backdrop_path"),
            vote_average=details.get("vote_average"),
            vote_count=details.get("vote_count"),
            budget=details.get("budget"),
            revenue=details.get("revenue"),
        )
        created_film = True

        for genre_data in details.get("genres", []):  # жанры без дублей
            genre, _ = Genre.objects.get_or_create(
                tmdb_id=genre_data["id"],
                defaults={"name": genre_data["name"]}
            )
            film.genres.add(genre)

        for idx, actor_data in enumerate(credits.get("cast", [])[:20]):  # актеры без дублей
            actor, _ = Actor.objects.get_or_create(
                tmdb_id=actor_data["id"],
                defaults={
                    "name": actor_data["name"],
                    "original_name": actor_data.get("original_name"),
                    "profile_path": actor_data.get("profile_path"),
                }
            )
            FilmActor.objects.create(
                film=film,
                actor=actor,
                character=actor_data.get("character"),
                order=idx
            )

        important_jobs = {"Director", "Writer", "Producer", "Composer"}

        for crew_data in credits.get("crew", []):
            if crew_data["job"] not in important_jobs:
                continue

            person, _ = Person.objects.get_or_create(   # режиссер, сценарист, продюсер, композитор без дублей
                tmdb_id=crew_data["id"],
                defaults={
                    "name": crew_data["name"],
                    "original_name": crew_data.get("original_name"),
                    "profile_path": crew_data.get("profile_path"),
                }
            )
            FilmCrew.objects.get_or_create(
                film=film,
                person=person,
                job=crew_data["job"]
            )

    user_film, created_user_film = UserFilm.objects.get_or_create(user=user, film=film)  # проверяем, есть ли фильм у пользователя

    return film, created_film, user_film, created_user_film


def build_poster_url(path: str | None) -> str | None:
    if not path:
        return None
    return f"https://image.tmdb.org/t/p/w342{path}"


def extract_year(release_date: str | None) -> str:
    return release_date[:4] if release_date else "—"


def join_genres(genre_ids, genre_map, limit=2) -> str:
    if not genre_ids or not genre_map:
        return ""
    return ", ".join(
        genre_map[g] for g in genre_ids[:limit] if g in genre_map
    )


def build_film_card(
    *,
    film: Film | None = None,
    tmdb_item: dict | None = None,
    genre_map: dict | None = None,
    user=None,
) -> dict:
    """Возвращает единый формат карточки фильма для film_preview_card.html"""
    if film:
        user_film = get_user_film(user, film) if user else None

        return {
            "tmdb_id": film.tmdb_id,
            "title": film.title,
            "poster_url": build_poster_url(film.poster_path),
            "release_date": film.release_date.year if film.release_date else "—",
            "genres": ", ".join(g.name for g in film.genres.all()[:2]),
            "rating": round(film.vote_average, 1) if film.vote_average else None,
            "in_library": True,
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


def build_recommendation_cards(user, limit=4) -> list[dict]:
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


def build_tmdb_collection_cards(films, user=None):
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


def map_status(user_film, has_review: bool, rating: float | None):
    """Формирует пользовательский статус фильма для карточки фильма"""
    if user_film is None:    # нет в списке Мои фильмы
        return {
            "is_favorite": False,
            "has_review": False,
            "user_rating": None,
            "rating_color": None,
        }

    rating_color = None
    if has_review:     # просмотрен - есть Review
        if rating is None:
            rating_color = "medium"
        elif rating >= 8.0:
            rating_color = "high"
        elif rating >= 5.0:
            rating_color = "medium"
        else:
            rating_color = "low"

    return {
        "is_favorite": user_film.is_favorite,
        "has_review": has_review,
        "user_rating": rating if has_review else None,
        "rating_color": rating_color,
    }


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


def format_nums(value: int | None) -> int | str:
    if not value:
        return "-"
    return f"{int(value):,}"
