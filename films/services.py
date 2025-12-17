from services.tmdb import Tmdb


tmdb = Tmdb()

def get_film_by_id(tmdb_id):
    film_inf = tmdb.get_movie_details(tmdb_id)
    cast_if = tmdb.get_credits(tmdb_id)
    return {

    }

def build_film_context():
    pass