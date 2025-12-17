from services.tmdb import Tmdb


tmdb = Tmdb()

def get_movie_data(tmdb_id):
    return tmdb.get_movie_details(tmdb_id)


def get_movie_credits(tmdb_id):
    return tmdb.get_credits(tmdb_id)


def get_crew_by_job(film, job):
    return film.filmcrew_set.filter(job=job).select_related("person")


def get_crew_member(credits, job):
    return next((p for p in credits.get("crew", []) if p.get("job") == job), None)


def build_film_context(*, film=None, tmdb_data=None, credits=None):
    """
    Возвращает единый контекст для шаблона film_detail.html
    """
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

    raise ValueError("build_film_context: no data provided")
