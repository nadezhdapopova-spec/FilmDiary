from typing import Optional
from django.db import transaction

from django.core.cache import cache

from films.models import Film, Genre, Actor, FilmActor, Person, FilmCrew
from services.tmdb import Tmdb


tmdb = Tmdb()

def get_movie_data(tmdb_id):
    """Возвращает подробные данные о фильме из API TMDB"""
    return tmdb.get_movie_details(tmdb_id)


def get_movie_credits(tmdb_id):
    """Возвращает данные об актерах и создателях фильма из API TMDB"""
    return tmdb.get_credits(tmdb_id)


def get_crew_by_job(film, job):
    """Возвращает данные из БД о создателе фильма по конкретной должности"""
    return [fc for fc in film.filmcrew_set.all() if fc.job == job]


def get_crew_member(credits, job):
    """Возвращает данные из API TMDB о создателе фильма по конкретной должности"""
    return next((p for p in credits.get("crew", []) if p.get("job") == job), None)


def build_film_context(*, film=None, tmdb_data=None, credits=None):
    """Возвращает единый контекст для шаблона film_detail.html из БД или из API TMDB"""
    if film:
        return {
            "source": "db",
            "in_library": True,

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
            "release_date": film.release_date,
            "budget": film.budget,
            "revenue": film.revenue,
            "production_company": film.production_company,

            "rating": film.vote_average,
            "vote_count": film.vote_count
        }

    if tmdb_data and credits:
        director = get_crew_member(credits, "Director")
        writer = get_crew_member(credits, "Writer")
        composer = get_crew_member(credits, "Composer")
        producer = get_crew_member(credits, "Producer")

        return {
            "source": "tmdb",
            "in_library": False,

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
            "director": director.get("name") if director else None,
            "writer": writer.get("name") if writer else None,
            "composer": composer.get("name") if composer else None,
            "producer": producer.get("name") if producer else None,

            "original_country": (
                tmdb_data.get("origin_country")[0]
                if tmdb_data.get("origin_country")
                else None
            ),
            "runtime": tmdb_data.get("runtime"),
            "release_date": tmdb_data.get("release_date"),
            "budget": tmdb_data.get("budget"),
            "revenue": tmdb_data.get("revenue"),
            "production_company": (
                tmdb_data["production_companies"][0]["name"]
                if tmdb_data.get("production_companies")
                else None
            ),

            "rating": tmdb_data.get("vote_average"),
            "vote_count": tmdb_data.get("vote_count")
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
    film = Film.objects.filter(tmdb_id=tmdb_id, user=user).first()  # проверяем, есть ли уже фильм у пользователя
    if film:
        return film, False

    payload = get_tmdb_movie_payload(tmdb_id)  # получаем TMDB данные из кэша
    if not payload:
        print(f"TMDB API returned None for tmdb_id={tmdb_id}")
        return None, False

    if "details" not in payload:
        print(f"No 'details' in payload for tmdb_id={tmdb_id}: {payload}")
        return None, False
    details = payload["details"]
    credits = payload["credits"]

    film = Film.objects.create(  # создаем фильм
        user=user,
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

    return film, True


def map_status(user_film):
    """Формирует пользовательский статус фильма для карточки фильма"""
    if user_film is None:
        return {"status": "none"}

    if user_film.is_watched:
        if user_film.rating is not None:
            if user_film.rating >= 8:
                rating_color = "high"
            elif user_film.rating >= 5:
                rating_color = "medium"
            else:
                rating_color = "low"
        else:
            rating_color = "medium"

        return {
            "status": "watched",
            "rating": user_film.rating,
            "rating_color": rating_color,
            "is_favorite": user_film.is_favorite,
        }

    if not user_film.is_watched:
        return {"status": "planned"}

    return {"status": "none"}


def search_tmdb_film(query: str, user, page_num: int=1) -> list[dict]:
    """Поиск по фильмам TMDB: возвращает список словарей для отображения фильмов (словарь=фильм)"""
    if not query:
        return []

    data = tmdb.search_movie(query=query, page=page_num)
    results = data.get("results", [])  or []
    if not results:
        return []

    ids = [item.get("id") for item in results if item.get("id")]

    user_films_qs = Film.objects.filter(tmdb_id__in=ids, user=user)
    user_films = {film.tmdb_id: film for film in user_films_qs}
    existing = set(user_films.keys())  # получаем ВСЕ фильмы пользователя одним запросом

    all_genre_ids = set(
        g_id
        for item in results
        for g_id in item.get("genre_ids", [])
    )
    genres_qs = Genre.objects.filter(tmdb_id__in=all_genre_ids)  # формируем один раз для запроса
    genre_map = {g.tmdb_id: g.name for g in genres_qs}

    films: list[dict] = []
    for item in results:
        tmdb_id = item.get("id")
        user_film = user_films.get(tmdb_id)
        genre_ids = item.get("genre_ids", []) or []
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
                "genres": ", ".join([genre_map.get(g_id) for g_id in genre_ids[:2] if g_id in genre_map]),
                "rating": round(float(item.get("vote_average", 0)), 1),
                "in_library": tmdb_id in existing,
            }
        film_dict.update(map_status(user_film))  # получаем и добавляем пользовательский статус фильма
        films.append(film_dict)
    films.sort(key=lambda f: f["rating"], reverse=True)

    return films


def search_user_film(query: str, user, page_num: int = 1) -> list[dict]:
    """Поиск по фильмам пользователя из БД"""

    films_qs = Film.objects.filter(
        user=user,
        title__icontains=query
    ).prefetch_related("genres", "actors", "crew")[(page_num - 1) * 12: page_num * 12]

    films = []
    for film in films_qs:
        film_dict = {
            "tmdb_id": film.tmdb_id,
            "title": film.title,
            "poster_url": f"https://image.tmdb.org/t/p/w342{film.poster_path}" if film.poster_path else None,
            "release_date": film.release_date.year if film.release_date else "----",
            "genres": ", ".join([g.name for g in film.genres.all()[:2]]),
            "rating": round(film.vote_average or 0, 1),
            "in_library": True,
            "created_at": film.created_at
        }
        film_dict.update(map_status(film))  # статус текущего фильма
        films.append(film_dict)

    films.sort(key=lambda f: f["created_at"], reverse=True)
    return films

def search_films(query: str, user, page_num: int=1, source: str = 'tmdb') -> list[dict]:
    """
    Поиск фильмов: "tmdb_film" — глобальный поиск по TMDB,
                   "user_film" — поиск по фильмам пользователя из БД
    """
    if not query:
        return []

    if source == 'user_films':
        return search_user_film(query, user, page_num)
    else:
        return search_tmdb_film(query, user, page_num)
