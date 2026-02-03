from films.services.utils import build_poster_url, extract_year, format_nums, join_genres


def test_format_nums():
    """Проверка перевода целого числа в строку формата 333,000,000"""
    assert format_nums(1000000) == "1,000,000"
    assert format_nums(None) == "-"
    assert format_nums(0) == "-"


def test_build_poster_url():
    """Проверка сборки полного url для постера фильма"""
    assert build_poster_url("/a.jpg") == "https://image.tmdb.org/t/p/w342/a.jpg"
    assert build_poster_url(None) is None


def test_extract_year():
    """Проверка получения года выхода фильма из даты релиза"""
    assert extract_year("2024-01-01") == "2024"
    assert extract_year(None) == "—"


def test_join_genres():
    """Проверка генерации строки с жанрами через запятую"""
    genre_map = {1: "Action", 2: "Drama"}
    assert join_genres([1, 2], genre_map) == "Action, Drama"
    assert join_genres([], genre_map) == ""
    assert join_genres([3], genre_map) == ""
