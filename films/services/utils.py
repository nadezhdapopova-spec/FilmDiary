def format_nums(value: int | None) -> str:
    """Переводит целое число в строку формата 333,000,000"""
    if not value:
        return "-"
    return f"{int(value):,}"


def build_poster_url(path: str | None) -> str | None:
    """Собирает полный url для постера фильма"""
    if not path:
        return None
    return f"https://image.tmdb.org/t/p/w342{path}"


def extract_year(release_date: str | None) -> str:
    """Получает дату релиза фильма и возвращает года выхода"""
    return release_date[:4] if release_date else "—"


def join_genres(genre_ids, genre_map, limit=2) -> str:
    """Возвращает строку с жанрами через запятую"""
    if not genre_ids or not genre_map:
        return ""
    return ", ".join(genre_map[g] for g in genre_ids[:limit] if g in genre_map)
