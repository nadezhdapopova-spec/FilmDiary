from datetime import datetime

from films.services.utils import format_nums


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
            "vote_count": format_nums(film.vote_count),
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
            "original_country": (tmdb_data.get("origin_country")[0] if tmdb_data.get("origin_country") else None),
            "runtime": tmdb_data.get("runtime"),
            "release_date": f"{release_date} г.",
            "release_year": release_year,
            "budget": format_nums(tmdb_data.get("budget")),
            "revenue": format_nums(tmdb_data.get("revenue")),
            "production_company": (
                tmdb_data["production_companies"][0]["name"] if tmdb_data.get("production_companies") else None
            ),
            "rating": round(tmdb_data.get("vote_average"), 1),
            "user_rating": None,
            "has_review": False,
            "is_favorite": False,
            "rating_color": None,
            "vote_count": format_nums(tmdb_data.get("vote_count")),
        }
    return None


def get_crew_by_job(film, job):
    """Возвращает данные из БД о создателе фильма по конкретной должности"""
    return [fc for fc in film.filmcrew_set.all() if fc.job == job]


def get_crew_member(credits, job):
    """Возвращает данные из API TMDB о создателе фильма по конкретной должности"""
    return next((p for p in credits.get("crew", []) if p.get("job") == job), None)
