from django.core.cache import cache

from films.models import UserFilm


def get_user_film(user, film):
    """Возвращает фильм, если пользователь авторизован и у него есть данный фильм в коллекции"""
    if not user.is_authenticated:
        return None
    return UserFilm.objects.filter(user=user, film=film).first()


def map_status(user_film, has_review: bool, rating: float | None):
    """Формирует пользовательский статус фильма для карточки фильма"""
    if user_film is None:  # нет в списке Мои фильмы
        return {
            "is_favorite": False,
            "has_review": False,
            "user_rating": None,
            "rating_color": None,
        }

    rating_color = None
    if has_review:  # просмотрен - есть Review
        if rating is None:
            rating_color = "medium"
        elif rating >= 8.0:
            rating_color = "high"
        elif rating >= 5.0:
            rating_color = "medium"
        else:
            rating_color = "low"

    return {
        "is_favorite": user_film.is_favorite,
        "has_review": has_review,
        "user_rating": rating if has_review else None,
        "rating_color": rating_color,
    }


def get_user_recommendations(user, *, limit=None):
    """Берет вычесленные для пользователя рекомендации из кэша"""
    if not user.is_authenticated:
        return []
    recs = cache.get(f"recs:user:{user.id}", [])
    return recs[:limit] if limit else recs
