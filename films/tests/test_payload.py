from unittest.mock import Mock

from films.services.tmdb_movie_payload import get_tmdb_movie_payload


def test_get_tmdb_movie_payload_from_cache(monkeypatch):
    """Берет данные о фильме из TMDB из кэша"""
    monkeypatch.setattr(
        "films.services.tmdb_movie_payload.cache.get",
        lambda key: {"details": {}, "credits": {}}
    )
    data = get_tmdb_movie_payload(1)
    assert "details" in data


def test_get_tmdb_movie_payload_cache_hit(monkeypatch):
    """Тест попадания в кэш"""
    mock_cache_get = Mock(return_value={"details": {}})
    monkeypatch.setattr("django.core.cache.cache.get", mock_cache_get)

    result = get_tmdb_movie_payload(123)
    mock_cache_get.assert_called_once_with("tmdb:movie:123")
    assert result == {"details": {}}


def test_get_tmdb_movie_payload_cache_miss(monkeypatch):
    """Тест промаха кэша и сохранения"""
    monkeypatch.setattr("django.core.cache.cache.get", Mock(return_value=None))
    mock_details = {"title": "Test"}
    mock_credits = {"cast": []}
    monkeypatch.setattr("services.tmdb", Mock(get_movie_details=lambda id: mock_details, get_credits=lambda id: mock_credits))
    mock_cache_set = Mock()
    monkeypatch.setattr("django.core.cache.cache.set", mock_cache_set)

    result = get_tmdb_movie_payload(123)

    assert "details" in result
    mock_cache_set.assert_called()
