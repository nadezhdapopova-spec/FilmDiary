from typing import Optional

from django.core.cache import cache

from services.tmdb import Tmdb


tmdb = Tmdb()


def get_tmdb_movie_payload(tmdb_id: int) -> Optional[dict]:
    """Кэширует данные из TMDB, если их еще нет, или возвращает данные из кэша (TTL: 12 часов)"""
    cache_key = f"tmdb:movie:{tmdb_id}"

    data = cache.get(cache_key)
    if data:
        return data

    details = tmdb.get_movie_details(tmdb_id)
    credits = tmdb.get_credits(tmdb_id)
    if not details or not credits:
        print(f"TMDB API failed: details={details}, credits={credits}")
        return None
    data = {
        "details": details,
        "credits": credits,
    }
    cache.set(cache_key, data, timeout=60 * 60 * 12)  # 12 часов
    return data
