from django.db import transaction

from films.models import Actor, Film, FilmActor, FilmCrew, Genre, Person, UserFilm
from films.services.tmdb_movie_payload import get_tmdb_movie_payload


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
            genre, _ = Genre.objects.get_or_create(tmdb_id=genre_data["id"], defaults={"name": genre_data["name"]})
            film.genres.add(genre)

        for idx, actor_data in enumerate(credits.get("cast", [])[:20]):  # актеры без дублей
            actor, _ = Actor.objects.get_or_create(
                tmdb_id=actor_data["id"],
                defaults={
                    "name": actor_data["name"],
                    "original_name": actor_data.get("original_name"),
                    "profile_path": actor_data.get("profile_path"),
                },
            )
            FilmActor.objects.create(film=film, actor=actor, character=actor_data.get("character"), order=idx)

        important_jobs = {"Director", "Writer", "Producer", "Composer"}

        for crew_data in credits.get("crew", []):
            if crew_data["job"] not in important_jobs:
                continue

            person, _ = Person.objects.get_or_create(  # режиссер, сценарист, продюсер, композитор без дублей
                tmdb_id=crew_data["id"],
                defaults={
                    "name": crew_data["name"],
                    "original_name": crew_data.get("original_name"),
                    "profile_path": crew_data.get("profile_path"),
                },
            )
            FilmCrew.objects.get_or_create(film=film, person=person, job=crew_data["job"])

    user_film, created_user_film = UserFilm.objects.get_or_create(
        user=user, film=film
    )  # проверяем, есть ли фильм у пользователя

    return film, created_film, user_film, created_user_film
