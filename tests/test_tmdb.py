from unittest.mock import Mock

from services.tmdb import Tmdb

def test_make_cache_key_stable():
    """Проверка ключей из кэша"""
    key1 = Tmdb._make_cache_key("tmdb", "/movie", {"a": 1, "b": 2})
    key2 = Tmdb._make_cache_key("tmdb", "/movie", {"b": 2, "a": 1})

    assert key1 == key2


def test_get_uses_cache(monkeypatch):
    """Тест работы кэша"""
    api = Tmdb()
    monkeypatch.setattr("services.tmdb.cache.get", lambda k: {"cached": True})
    result = api._get("/test")

    assert result == {"cached": True}


def test_get_http_success(monkeypatch):
    """Успешное подключение и получение информации из TMDB"""
    api = Tmdb()
    response = Mock()
    response.json.return_value = {"ok": True}
    response.raise_for_status.return_value = None
    monkeypatch.setattr("services.tmdb.requests.get", lambda *a, **k: response)
    monkeypatch.setattr("services.tmdb.cache.get", lambda k: None)
    monkeypatch.setattr("services.tmdb.cache.set", lambda *a, **k: None)
    result = api._get("/test")

    assert result == {"ok": True}


def test_build_tmdb_film(monkeypatch):
    """Проверяет построение фильма из TMDB"""
    api = Tmdb()
    monkeypatch.setattr(api, "get_movie_details", lambda _: {
        "title": "Test",
        "overview": "overview",
        "tagline": "",
        "genres": [{"name": "Action"}],
    })
    monkeypatch.setattr(api, "get_credits", lambda _: {
        "cast": [{"name": "Actor"}],
        "crew": [{"job": "Director", "name": "Director"}],
    })
    raw = {"id": 123}
    film = api._build_tmdb_film(raw)

    assert film.tmdb_id == 123
    assert film.genres == ["action"]
    assert film.actors == ["actor"]
    assert film.director == "director"
