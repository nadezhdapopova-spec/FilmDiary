import pytest
from datetime import datetime, timedelta

from services.recommendations import build_recommendations


class DummyFilm:
    def __init__(
        self,
        tmdb_id: int,
        title: str,
        genres,
        actors,
        director=None,
        overview="",
        tagline="",
    ):
        self.tmdb_id = tmdb_id
        self.title = title
        self.genres = genres
        self.actors = actors
        self.director = director
        self.overview = overview
        self.tagline = tagline


class DummyFilmRef:
    def __init__(self, tmdb_id, title):
        self.tmdb_id = tmdb_id
        self.title = title


class DummyReview:
    def __init__(self, film, rating, days_ago=0):
        self.film = film
        self.user_rating = rating
        self.updated_at = datetime.now() - timedelta(days=days_ago)


class DummyUser:
    def __init__(self, reviews):
        self._reviews = reviews

    @property
    def reviews(self):
        return self

    def select_related(self, *_):
        return self._reviews


class DummyTmdb:
    def __init__(self, films):
        self._films = films

    def get_candidate_pool(self):
        return self._films

    def get_genres(self):
        return []

    def get_movies_by_genre(self, *_):
        return []


@pytest.mark.parametrize("rating", [8, 10])
def test_build_recommendations_returns_candidates(rating):
    """
    Интеграционный тест build_recommendations:
    - учитываются признаки (жанры, актёры)
    - просмотренные фильмы исключаются
    - возвращается нормализованный score и reasons
    """
    watched_film = DummyFilm(
        tmdb_id=1,
        title="Watched Film",
        genres=["Action"],
        actors=["Actor A"],
        director="Director A",
        overview="Action movie with hero",
    )
    review = DummyReview(
        film=DummyFilmRef(1, "Watched Film"),
        rating=rating,
        days_ago=1,
    )
    user = DummyUser([review])
    candidate_1 = DummyFilm(
        tmdb_id=2,
        title="Similar Action",
        genres=["Action"],
        actors=["Actor A"],
        director="Director B",
        overview="Another action movie",
    )
    candidate_2 = DummyFilm(
        tmdb_id=3,
        title="Different Genre",
        genres=["Comedy"],
        actors=["Actor X"],
        director="Director X",
        overview="Funny comedy",
    )
    api = DummyTmdb([watched_film, candidate_1, candidate_2])
    recs = build_recommendations(user, api)

    assert isinstance(recs, list)
    assert recs, "Должны быть рекомендации"
    rec_ids = {r["tmdb_id"] for r in recs}
    assert 1 not in rec_ids
    assert 2 in rec_ids
    rec = recs[0]
    assert "score" in rec
    assert 0 < rec["score"] <= 1.0
    assert "reasons" in rec
    assert isinstance(rec["reasons"], list)
    assert rec["reasons"], "Должны быть объяснения"
