from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import render
from django.views.generic import TemplateView

from films.models import Film
from films.services import build_film_context, get_tmdb_movie_payload, search_films, get_user_film
from reviews.models import Review


class FilmDetailView(LoginRequiredMixin, TemplateView):
    """Представление для отображения подробной информации о фильме"""
    template_name = "films/film_detail.html"
    context_object_name = "film"

    def get_context_data(self, **kwargs):
        """
        Возвращает карточку фильма: если фильм есть в персональной БД, берет данные из БД,
        если нет - формирует из данных сайта TMDB
        """
        context = super().get_context_data(**kwargs)
        tmdb_id = self.kwargs["tmdb_id"]

        film_obj = (
            Film.objects.filter(tmdb_id=tmdb_id).prefetch_related("genres", "actors", "crew",).first()
        )
        user_film = None
        review = None

        if film_obj:
            user_film = get_user_film(self.request.user, film_obj)  # model

            if user_film:
                review = Review.objects.filter(
                    user=self.request.user,
                    film=film_obj
                ).first()

            film_data = build_film_context(film=film_obj)  # dict для шаблона

        else:
            payload = get_tmdb_movie_payload(tmdb_id)
            if not payload:
                raise Http404("Фильм не найден")

            film_data = build_film_context(
                tmdb_data=payload["details"],
                credits=payload["credits"]
            )

        if not film_data:
            raise Http404("Фильм не найден")

        film_data.update({
            "in_library": bool(user_film),
            "has_review": bool(review),
            "user_rating": review.user_rating if review else None,
            "is_favorite": user_film.is_favorite if user_film else False,
            })

        context["film"] = film_data
        context["user_film"] = user_film
        context["review"] = review
        return context


def film_search_view(request):
    """Осуществляет универсальный поисковый запрос фильма: по TMDB или фильмам пользователя"""

    query = request.GET.get("q", "").strip()
    source = request.GET.get("source", "tmdb")  # 'tmdb' или 'user_films' или 'favorites'
    params = f"&q={query}&source={source}" if query else ""
    page_number = request.GET.get("page", 1)

    results = search_films(source=source, query=query, page_num=page_number, user=request.user)

    is_user_films = source in ["user_films", "favorites", "watched", "reviewed"]
    paginator = Paginator(results, 12)
    page_obj = paginator.get_page(page_number)

    context = {
        "search_type": source,
        "is_user_films": is_user_films,
        "query": query,
        "page_obj": page_obj,
        "params": params,
        "view_url": "films:film_search",
        "template": "search",
    }
    return render(request, "films/film_search.html", context)
