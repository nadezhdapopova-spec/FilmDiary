from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import render
from django.views.generic import TemplateView

from films.models import Film
from films.services.context import build_film_context
from films.services.search import search_films
from films.services.tmdb_movie_payload import get_tmdb_movie_payload
from films.services.user_film_services import get_user_film
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
            Film.objects.filter(tmdb_id=tmdb_id)
            .prefetch_related(
                "genres",
                "actors",
                "crew",
            )
            .first()
        )

        user_film = None
        review = None

        if film_obj:
            user_film = get_user_film(self.request.user, film_obj)  # model

            if user_film:
                review = Review.objects.filter(user=self.request.user, film=film_obj).first()

            film_data = build_film_context(film=film_obj)  # dict для шаблона

        else:
            payload = get_tmdb_movie_payload(tmdb_id)
            if not payload:
                raise Http404("Фильм не найден")

            film_data = build_film_context(tmdb_data=payload["details"], credits=payload["credits"])

        if not film_data:
            raise Http404("Фильм не найден")

        film_data.update(
            {
                "in_library": bool(user_film),
                "has_review": bool(review),
                "user_rating": review.user_rating if review else None,
                "is_favorite": user_film.is_favorite if user_film else False,
            }
        )

        context["film"] = film_data
        context["user_film"] = user_film
        context["review"] = review
        return context


def film_search_view(request):
    """Осуществляет универсальный поисковый запрос фильма: по TMDB или фильмам пользователя"""

    query = request.GET.get("q", "").strip()
    source = request.GET.get("source", "tmdb")  # 'tmdb' или 'user_films' или 'favorites'
    params = f"&q={query}&source={source}" if query else ""
    page_number = int(request.GET.get("page", 1))
    user = request.user if request.user.is_authenticated else None
    results = search_films(query=query, user=user, page_num=1, source=source)

    is_user_films = source in ["user_films", "favorites", "watched", "reviewed"]
    is_tmdb = source == "tmdb"
    paginator = Paginator(results, 12)
    page_obj = paginator.get_page(page_number)

    context = {
        "search_type": source,
        "is_user_films": is_user_films,
        "is_tmdb": is_tmdb,
        "query": query,
        "page_obj": page_obj,
        "items": page_obj.object_list,
        "params": params,
        "view_url": "films:film_search",
        "template": "search",
        "is_search_context": True,
    }
    return render(request, "films/film_search.html", context)
