from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import ListView, TemplateView

from calendar_events.models import CalendarEvent
from films.models import UserFilm
from films.services import save_film_from_tmdb
from reviews.models import Review


class HomeView(TemplateView):
    template_name = "films/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if self.request.user.is_authenticated:
            context.update({
                "recs_for_me": get_user_recommendations(self.request.user, limit=4),
                # "planned_movies": get_planned(self.request.user, limit=4),
                # "recent_movies": get_recent(self.request.user, limit=4),
            })

        context["search_type"] = "films"  # всегда для search_bar
        return context


class RecommendsView(LoginRequiredMixin, TemplateView):
    template_name = "films/recommends.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["recommendations"] = get_user_recommendations(self.request.user, limit=50)
        return context


class UserListFilmView(LoginRequiredMixin, ListView):
    """Представление для отображения списка 'Мои фильмы'"""

    model = UserFilm
    context_object_name = "items"
    paginate_by = 12
    template_name = "films/my_films.html"

    def get_queryset(self):
        """Возвращает список пользователя 'Мои фильмы', осуществляет поиск по q"""
        queryset = (UserFilm.objects
                    .filter(user=self.request.user, film__tmdb_id__isnull=False)
                    .select_related("film")
                    .order_by("-created_at"))

        query = self.request.GET.get("q", "").strip()
        if query:
            queryset = queryset.filter(film__title__icontains=query)

        return queryset

    def get_context_data(self, **kwargs):
        """Добавляет данные в контекст для поиска"""
        context = super().get_context_data(**kwargs)
        items = context[self.context_object_name]  # список user_films на странице

        film_ids = [uf.film_id for uf in items]
        reviews_map = {r.film_id: r for r in Review.objects.filter(user=self.request.user, film_id__in=film_ids)} # Получаем все отзывы пользователя на фильмы из текущего queryset

        planned_film_ids = set(
            CalendarEvent.objects
            .filter(user=self.request.user, film_id__in=film_ids, planned_date__gte=timezone.now().date())
            .values_list("film_id", flat=True)
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
        queryset = UserFilm.objects.filter(
            user=self.request.user,
            is_favorite=True
        ).select_related("film").order_by("-created_at")

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
            return JsonResponse({"status": "error", "message": "Нет ID фильма"}, status=400)

        try:
            film, created_film, user_film, created_user_film = save_film_from_tmdb(
                tmdb_id=int(tmdb_id),
                user=request.user
            )
        except Exception:
            return JsonResponse({"status": "error", "message": "Ошибка при сохранении фильма"}, status=500)

        if not film or not user_film:
            return JsonResponse({"status": "error", "message": "Фильм не найден или не удалось сохранить"}, status=500)

        if created_user_film:
            return JsonResponse({"status": "added"})
        return JsonResponse({"status": "exists"})


class UpdateFilmStatusView(LoginRequiredMixin, View):
    """Обновляет статус фильма"""

    def post(self, request, *args, **kwargs):
        tmdb_id = request.POST.get("tmdb_id")
        action = request.POST.get("action")  # 'plan' или 'favorite'

        try:
            user_film = UserFilm.objects.select_related("film").get(user=request.user, film__tmdb_id=tmdb_id)

            if action == "watch":
                return JsonResponse({
                    "status": "redirect",
                    "url": reverse("reviews:review_create", kwargs={"tmdb_id": user_film.film.tmdb_id})
                })
            elif action == "favorite":
                user_film.is_favorite = True
            elif action == "delete":
                user_film.delete()
                return JsonResponse({
                    "status": "success",
                    "action": action,
                    "removed": True
                })
            elif action == "unfavorite":
                user_film.is_favorite = False
                user_film.save()
                return JsonResponse({
                    "status": "success",
                    "action": action,
                    "is_favorite": user_film.is_favorite
                })
            elif action == "delete-watched":
                Review.objects.filter(user=request.user, film=user_film.film).delete()
                return JsonResponse({
                    "status": "success",
                    "action": action,
                    "is_favorite": user_film.is_favorite,
                    "has_review": False,
                    "user_rating": None
                })
            user_film.save()
            review = Review.objects.filter(user=request.user, film=user_film.film).only("user_rating").first()
            return JsonResponse({
                "status": "success",
                "action": action,
                "is_favorite": user_film.is_favorite,
                "has_review": bool(review),
                "user_rating": review.user_rating if review else None
            })
        except UserFilm.DoesNotExist:
            return JsonResponse({"status": "error", "message": "Фильм не найден"}, status=404)
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)


class DeleteFilmView(LoginRequiredMixin, View):
    """Представление для удаления фильма из коллекции пользователя"""

    def post(self, request, *args, **kwargs):
        """Удаляет фильм из коллекции пользователя"""
        tmdb_id = self.kwargs["tmdb_id"]
        # print(tmdb_id)
        # print("Deleting UserFilm:", UserFilm.objects.filter(user=request.user, film__tmdb_id=tmdb_id).query)
        # print("Deleting Review:", Review.objects.filter(user=request.user, film__tmdb_id=tmdb_id).query)

        Review.objects.filter(user=request.user, film__tmdb_id=tmdb_id).delete()
        UserFilm.objects.filter(user=request.user, film__tmdb_id=tmdb_id).delete()

        messages.info(request, "Фильм успешно удалён")
        return redirect("films:my_films")


def get_user_recommendations(user, *, limit=None):
    if not user.is_authenticated:
        return []
    recs = cache.get(f"recs:user:{user.id}", [])
    # if not recs:
    #     return {
    #         "status": "pending",
    #         "message": "Добавляй фильмы в просмотренное — рекомендации скоро появятся"
    #     }
    return recs[:limit] if limit else recs


def custom_error(request, status_code=404, exception=None):
    """Универсальная обработка всех ошибок status_code: 400, 403, 404, 500"""
    context = {
        "status_code": status_code,
        "exception": str(exception)[:100] if exception else None,
    }
    return render(request, "error_page.html", context, status=status_code)
