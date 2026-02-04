import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import ListView, TemplateView

from calendar_events.models import CalendarEvent
from films.models import UserFilm
from films.services.builders import build_recommendation_cards, build_tmdb_collection_cards
from films.services.save_film import save_film_from_tmdb
from reviews.models import Review
from services.permissions import is_manager
from services.tmdb import Tmdb

logger = logging.getLogger("filmdiary.films")


class HomeView(TemplateView):
    template_name = "films/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if self.request.user.is_authenticated:
            recent_watched = (
                Review.objects.filter(user=self.request.user).select_related("film").order_by("-watched_at")[:5]
            )

            film_ids = [r.film_id for r in recent_watched]
            user_films = UserFilm.objects.filter(user=self.request.user, film_id__in=film_ids)
            user_films_map = {uf.film_id: uf for uf in user_films}

            recent_watched_with_status = []
            for review in recent_watched:
                recent_watched_with_status.append(
                    {
                        "film": review.film,
                        "user_film": user_films_map.get(review.film_id),
                        "review": review,
                        "is_favorite": bool(
                            user_films_map.get(review.film_id) and user_films_map[review.film_id].is_favorite
                        ),
                    }
                )

            context.update(
                {
                    "recs_for_me": build_recommendation_cards(self.request.user, limit=4),
                    "recent_watched": recent_watched_with_status,
                }
            )
        context["search_type"] = "tmdb"
        context["home_page"] = True
        return context


class FilmRecommendsView(LoginRequiredMixin, TemplateView):
    template_name = "films/film_recommends.html"
    paginate_by = 12

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        recommend_type = self.request.GET.get("type", "recommended")
        tmdb = Tmdb()

        title = ""
        cards = []

        if recommend_type == "recommended":
            title = "Персональные рекомендации"
            cards = build_recommendation_cards(self.request.user, limit=50)

        elif recommend_type == "popular":
            title = "Популярные фильмы"
            films = tmdb.get_popular(pages=3)
            cards = build_tmdb_collection_cards(films, user=self.request.user)

        elif recommend_type == "now_playing":
            title = "Сейчас в кино"
            films = tmdb.get_now_playing(pages=2)
            cards = build_tmdb_collection_cards(films, user=self.request.user)

        elif recommend_type == "upcoming":
            title = "Скоро в кино"
            films = tmdb.get_upcoming(pages=2)
            cards = build_tmdb_collection_cards(films, user=self.request.user)

        elif recommend_type == "trending":
            title = "Тренды недели"
            films = tmdb.get_trending().get("results", [])
            cards = build_tmdb_collection_cards(films, user=self.request.user)

        elif recommend_type == "top_rated":
            title = "Топ-рейтинговые фильмы"
            films = tmdb.get_top_rated(pages=2)
            cards = build_tmdb_collection_cards(films, user=self.request.user)

        paginator = Paginator(cards, self.paginate_by)
        page_number = self.request.GET.get("page")
        page_obj = paginator.get_page(page_number)
        params = self.request.GET.copy()
        params.pop("page", None)

        context.update(
            {
                "films": page_obj,
                "page_obj": page_obj,
                "is_paginated": page_obj.has_other_pages(),
                "params": f"&{params.urlencode()}" if params else "",
                "recommend_type": recommend_type,
                "recommend_title": title,
            }
        )
        return context


class UserListFilmView(LoginRequiredMixin, ListView):
    """Представление для отображения списка 'Мои фильмы'"""

    model = UserFilm
    context_object_name = "items"
    paginate_by = 12
    template_name = "films/my_films.html"

    def get_queryset(self):
        """Возвращает список пользователя 'Мои фильмы', осуществляет поиск по q"""
        if self.request.user.is_superuser or is_manager(self.request.user):
            queryset = UserFilm.objects.filter(film__tmdb_id__isnull=False).select_related("film")
        else:
            queryset = UserFilm.objects.filter(user=self.request.user, film__tmdb_id__isnull=False).select_related(
                "film"
            )

        query = self.request.GET.get("q", "").strip()
        if query:
            queryset = queryset.filter(film__title__icontains=query)
        return queryset.order_by("-created_at")

    def get_context_data(self, **kwargs):
        """Добавляет данные в контекст для поиска"""
        context = super().get_context_data(**kwargs)
        items = context[self.context_object_name]  # список user_films на странице

        film_ids = [uf.film_id for uf in items]
        reviews_map = {
            r.film_id: r for r in Review.objects.filter(user=self.request.user, film_id__in=film_ids)
        }  # Получаем все отзывы пользователя на фильмы из текущего queryset

        planned_film_ids = set(
            CalendarEvent.objects.filter(
                user=self.request.user, film_id__in=film_ids, planned_date__gte=timezone.now().date()
            ).values_list("film_id", flat=True)
        )

        context[self.context_object_name] = [
            {
                "user_film": uf,
                "review": reviews_map.get(uf.film_id),
                "is_planned": uf.film_id in planned_film_ids,
            }
            for uf in items
        ]
        query = self.request.GET.get("q", "").strip()
        context["search_type"] = "user_films"
        context["query"] = query
        context["params"] = f"&q={query}&source=user_films" if query else "&source=user_films"
        context["view_url"] = "films:my_films"
        context["template"] = "my_films"
        context["favorites_page"] = False

        return context


class FavoriteFilmsView(UserListFilmView):
    """Список любимых фильмов пользователя"""

    model = UserFilm
    context_object_name = "items"
    paginate_by = 12
    template_name = "films/my_films.html"

    def get_queryset(self):
        """Возвращает список пользователя 'Любимое', осуществляет поиск по q"""
        queryset = (
            UserFilm.objects.filter(user=self.request.user, is_favorite=True)
            .select_related("film")
            .order_by("-created_at")
        )

        query = self.request.GET.get("q", "").strip()
        if query:
            queryset = queryset.filter(film__title__icontains=query)

        return queryset

    def get_context_data(self, **kwargs):
        """Добавляет данные в контекст для поиска в списке любимых фильмов"""
        context = super().get_context_data(**kwargs)
        query = self.request.GET.get("q", "").strip()

        context["search_type"] = "favorites"  # любимые
        context["query"] = query
        context["params"] = f"&q={query}&source=favorites" if query else "&source=favorites"
        context["view_url"] = "films:favorite_films"
        context["favorites_page"] = True

        return context


class AddFilmView(LoginRequiredMixin, View):
    """Представление для добавления фильма в список 'Мои фильмы'"""

    def post(self, request, *args, **kwargs):
        """Добавляет фильм в список пользователя 'Мои фильмы'"""
        tmdb_id = request.POST.get("tmdb_id")

        if not tmdb_id:
            logger.warning("AddFilm: missing tmdb_id=%s", tmdb_id)
            return JsonResponse({"status": "error", "message": "Нет ID фильма"}, status=400)

        try:
            logger.debug("AddFilm: tmdb_id=%s user=%s", tmdb_id, request.user.id)
            film, created_film, user_film, created_user_film = save_film_from_tmdb(
                tmdb_id=int(tmdb_id), user=request.user
            )
        except Exception as e:
            logger.exception("AddFilm FAIL tmdb_id=%s: %s", tmdb_id, e)
            return JsonResponse({"status": "error", "message": "Ошибка при сохранении фильма"}, status=500)

        if not film or not user_film:
            logger.warning("AddFilm: no film/user_film tmdb_id=%s", tmdb_id)
            return JsonResponse({"status": "error", "message": "Фильм не найден или не удалось сохранить"}, status=500)

        if created_user_film:
            logger.info("AddFilm OK: new user_film=%s tmdb_id=%s", user_film.id, tmdb_id)
            return JsonResponse({"status": "added"})
        else:
            logger.debug("AddFilm OK: exists tmdb_id=%s", tmdb_id)
            return JsonResponse({"status": "exists"})


class UpdateFilmStatusView(LoginRequiredMixin, View):
    """Обновляет статус фильма"""

    def post(self, request, *args, **kwargs):
        tmdb_id = request.POST.get("tmdb_id")
        action = request.POST.get("action")  # 'plan' или 'favorite'

        try:
            user_film = UserFilm.objects.select_related("film").get(user=request.user, film__tmdb_id=tmdb_id)
            logger.debug("UpdateFilm: tmdb_id=%s action=%s", tmdb_id, action)

            if action == "watch":
                return JsonResponse(
                    {
                        "status": "redirect",
                        "url": reverse("reviews:review_create", kwargs={"tmdb_id": user_film.film.tmdb_id}),
                    }
                )
            elif action == "favorite":
                user_film.is_favorite = True
            elif action == "delete":
                user_film.delete()
                logger.info("UpdateFilm DELETE: tmdb_id=%s", tmdb_id)
                return JsonResponse({"status": "success", "action": action, "removed": True})
            elif action == "unfavorite":
                user_film.is_favorite = False
                user_film.save()
                return JsonResponse({"status": "success", "action": action, "is_favorite": user_film.is_favorite})
            elif action == "delete-watched":
                Review.objects.filter(user=request.user, film=user_film.film).delete()
                return JsonResponse(
                    {
                        "status": "success",
                        "action": action,
                        "is_favorite": user_film.is_favorite,
                        "has_review": False,
                        "user_rating": None,
                    }
                )
            user_film.save()

            review = Review.objects.filter(user=request.user, film=user_film.film).only("user_rating").first()
            logger.debug("UpdateFilm OK: tmdb_id=%s action=%s favorite=%s", tmdb_id, action, user_film.is_favorite)
            return JsonResponse(
                {
                    "status": "success",
                    "action": action,
                    "is_favorite": user_film.is_favorite,
                    "has_review": bool(review),
                    "user_rating": review.user_rating if review else None,
                }
            )
        except UserFilm.DoesNotExist:
            logger.warning("UpdateFilm: not found tmdb_id=%s user=%s", tmdb_id, request.user.id)
            return JsonResponse({"status": "error", "message": "Фильм не найден"}, status=404)
        except Exception as e:
            logger.exception("UpdateFilm FAIL tmdb_id=%s action=%s: %s", tmdb_id, action, e)
            return JsonResponse({"status": "error", "message": str(e)}, status=500)


class DeleteFilmView(LoginRequiredMixin, View):
    """Представление для удаления фильма из коллекции пользователя"""

    def post(self, request, *args, **kwargs):
        """Удаляет фильм из коллекции пользователя"""
        tmdb_id = self.kwargs["tmdb_id"]

        Review.objects.filter(user=request.user, film__tmdb_id=tmdb_id).delete()
        UserFilm.objects.filter(user=request.user, film__tmdb_id=tmdb_id).delete()

        messages.info(request, "Фильм успешно удалён")
        return redirect("films:my_films")


def custom_error(request, status_code=404, exception=None):
    """Универсальная обработка всех ошибок status_code: 400, 403, 404, 500"""
    context = {
        "status_code": status_code,
        "exception": str(exception)[:100] if exception else None,
    }
    return render(request, "error_page.html", context, status=status_code)
