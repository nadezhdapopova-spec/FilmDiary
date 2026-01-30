from datetime import date, timedelta
from unittest.mock import Mock

from services.recommendations import (
    fast_feature_weight,
    normalize_rating,
    recency_boost,
    final_rating_factor,
    final_recency_factor,
    FeatureCache,
    FilmIndex,
    weighted_jaccard_by_features,
    genre_similarity,
    compute_genre_boost_for_candidate,
    top_k_candidates_by_feature_weight, api_genre_candidates, TextSimilarity,
)


def test_fast_feature_weight_known_type():
    """Вес признака берётся из FEATURE_WEIGHTS по типу"""
    assert fast_feature_weight("genre:action") > 0


def test_fast_feature_weight_unknown_type():
    """Неизвестный тип признака даёт вес 1.0"""
    assert fast_feature_weight("unknown:something") == 1.0


def test_fast_feature_weight_empty():
    """Пустой признак даёт нейтральный вес"""
    assert fast_feature_weight("") == 1.0

def test_normalize_rating_middle():
    """Нормализация рейтинга внутри диапазона"""
    assert round(normalize_rating(5), 2) == 0.44


def test_normalize_rating_clamped_low():
    """Рейтинг ниже минимума зажимается"""
    assert normalize_rating(-10) == 0.0


def test_normalize_rating_clamped_high():
    """Рейтинг выше максимума зажимается"""
    assert normalize_rating(100) == 1.0

def test_recency_boost_today():
    """Сегодняшняя дата даёт максимальный вес"""
    assert recency_boost(date.today()) == 1.0


def test_recency_boost_old_date():
    """Чем старее дата, тем меньше вес"""
    old = date.today() - timedelta(days=365)
    assert recency_boost(old) < 1.0


def test_recency_boost_none():
    """Отсутствие даты не штрафует"""
    assert recency_boost(None) == 1.0


def test_final_rating_factor_never_zero():
    """Даже нулевой рейтинг даёт ненулевой вклад"""
    assert final_rating_factor(0.0) > 0.0


def test_final_recency_factor_never_zero():
    """Даже старый фильм даёт ненулевой вклад"""
    assert final_recency_factor(0.0) > 0.0


class DummyFilm:
    def __init__(self, tmdb_id, genres, actors, director=None):
        self.tmdb_id = tmdb_id
        self.genres = genres
        self.actors = actors
        self.director = director


def test_feature_cache_prepare_and_get():
    """FeatureCache сохраняет признаки фильма"""
    film = DummyFilm(
        tmdb_id=1,
        genres=["Action", "Drama"],
        actors=["Actor One"],
        director="Director"
    )

    cache = FeatureCache()
    cache.prepare_film(film)

    feats = cache.get_features(1)

    assert "genre:action" in feats
    assert "actor:actor one" in feats
    assert "director:director" in feats


def test_feature_cache_idempotent():
    """Повторная подготовка не ломает кэш"""
    film = DummyFilm(1, ["Action"], [], None)
    cache = FeatureCache()

    cache.prepare_film(film)
    cache.prepare_film(film)

    assert len(cache.get_features(1)) == 1

def test_film_index_candidates():
    """Индекс возвращает фильмы с хотя бы одним общим признаком"""
    idx = FilmIndex()
    idx.add_film(1, ["genre:sci-fi", "actor:a"])
    idx.add_film(2, ["genre:drama"])

    cand = idx.candidates_for(["genre:sci-fi"])

    assert cand == {1}

def test_top_k_candidates_returns_best():
    """Возвращаются фильмы с наибольшим суммарным весом"""
    idx = FilmIndex()
    idx.add_film(1, ["genre:action"])
    idx.add_film(2, ["genre:action", "director:nolan"])

    res = top_k_candidates_by_feature_weight(["genre:action"], idx, k=1)

    assert len(res) == 1

def test_weighted_jaccard_identical():
    """Одинаковые признаки дают сходство 1"""
    feats = ["genre:action", "actor:a"]
    assert weighted_jaccard_by_features(feats, feats) == 1.0


def test_weighted_jaccard_disjoint():
    """Нет общих признаков: 0"""
    assert weighted_jaccard_by_features(
        ["genre:action"],
        ["genre:drama"]
    ) == 0.0


def test_genre_similarity_partial():
    """Частичное пересечение жанров"""
    a = ["genre:action", "genre:drama"]
    b = ["genre:action", "genre:comedy"]

    assert genre_similarity(a, b) == 1 / 3


def test_genre_boost_max_strategy(monkeypatch):
    """Стратегия max берёт максимальную релевантность жанра"""
    monkeypatch.setattr("services.recommendations.GENRE_BOOST_STRATEGY","max")
    profile = {
        "genre:action": 0.8,
        "genre:drama": 0.4,
    }
    boost = compute_genre_boost_for_candidate(profile,{"genre:action", "genre:drama"})

    assert boost == 0.8


class DummyMovie:
    def __init__(self, tmdb_id):
        self.tmdb_id = tmdb_id

def test_api_genre_candidates_empty_profile():
    """Если пустой профиль у пользователя"""
    api = Mock()
    result = api_genre_candidates({}, api)
    assert result == set()

def test_api_genre_candidates_api_none():
    """Если api = None"""
    result = api_genre_candidates({"genre:action": 1.0}, None)
    assert result == set()

def test_api_genre_candidates_returns_ids(monkeypatch):
    """Успешный поиск кандидатов"""
    api = Mock()
    monkeypatch.setattr("services.recommendations.get_tmdb_genre_map", lambda api: {"action": 28, "drama": 18},)
    api.get_movies_by_genre.side_effect = [
        [DummyMovie(1), DummyMovie(2)],
        [DummyMovie(3)],
    ]
    profile = {
        "genre:action": 1.0,
        "genre:drama": 0.8,
    }
    result = api_genre_candidates(profile, api)

    assert result == {1, 2, 3}

def test_api_genre_candidates_respects_limit(monkeypatch):
    """Проверка установленных лимитов на количество кандидатов"""
    api = Mock()
    monkeypatch.setattr("services.recommendations.get_tmdb_genre_map", lambda api: {"action": 28},)
    api.get_movies_by_genre.return_value = [
        DummyMovie(1),
        DummyMovie(2),
        DummyMovie(3),
    ]
    profile = {"genre:action": 1.0}
    result = api_genre_candidates(profile, api, limit=2)

    assert len(result) == 2

def test_api_genre_candidates_api_exception(monkeypatch):
    """Ошибка при работе с API: API бросает исключение"""
    api = Mock()
    monkeypatch.setattr("services.recommendations.get_tmdb_genre_map", lambda api: {"action": 28},)
    api.get_movies_by_genre.side_effect = Exception("API error")
    result = api_genre_candidates({"genre:action": 1.0}, api)

    assert result == set()


class DummyFilmSimilarity:
    def __init__(self, tmdb_id, overview="", tagline=""):
        self.tmdb_id = tmdb_id
        self.overview = overview
        self.tagline = tagline

def test_text_similarity_identical_texts():
    """Одинаковые тексты: similarity ≈ 1"""
    films = [
        DummyFilmSimilarity(1, "hero saves world"),
        DummyFilmSimilarity(2, "hero saves world"),
    ]
    sim = TextSimilarity(films)
    score = sim.similarity(1, 2)

    assert score > 0.9

def test_text_similarity_different_texts():
    """Разные тексты: similarity низкий"""
    films = [
        DummyFilmSimilarity(1, "space ship galaxy"),
        DummyFilmSimilarity(2, "romantic comedy love"),
    ]
    sim = TextSimilarity(films)
    score = sim.similarity(1, 2)

    assert score < 0.3

def test_text_similarity_empty_texts():
    """Пустые тексты: similarity 0.0"""
    films = [
        DummyFilmSimilarity(1, "", ""),
        DummyFilmSimilarity(2, "", ""),
    ]

    sim = TextSimilarity(films)

    assert sim.similarity(1, 2) == 0.0

def test_text_similarity_unknown_id():
    """Неизвестный ID: similarity 0.0"""
    films = [
        DummyFilmSimilarity(1, "hello world"),
    ]
    sim = TextSimilarity(films)

    assert sim.similarity(1, 999) == 0.0
