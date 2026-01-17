from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import ListView, TemplateView

from films.models import UserFilm
from films.services import save_film_from_tmdb


class HomeView(TemplateView):
    template_name = "films/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if self.request.user.is_authenticated:
            context.update({
                # "recs_for_me": get_recommendations(self.request.user, limit=4),
                # "planned_movies": get_planned(self.request.user, limit=4),
                # "recent_movies": get_recent(self.request.user, limit=4),
            })

        context["search_type"] = "films"  # всегда для search_bar
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
        user_film_id = request.POST.get("film_id")
        action = request.POST.get("action")  # 'plan' или 'favorite'

        try:
            user_film = UserFilm.objects.get(id=user_film_id, user=request.user)

            if action == "plan":
                user_film.is_planned = True
            elif action == "watch":
                return JsonResponse({
                    "status": "redirect",
                    "url": reverse("reviews:review_create", kwargs={"film_id": user_film.film.id})
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
            user_film.save()
            return JsonResponse({
                "status": "success",
                "action": action,
                "is_planned": user_film.is_planned,
                "is_favorite": user_film.is_favorite
            })
        except UserFilm.DoesNotExist:
            return JsonResponse({"status": "error", "message": "Фильм не найден"}, status=404)
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)


class DeleteFilmView(LoginRequiredMixin, View):
    """Представление для удаления фильма из списка'Мои фильмы'"""

    def post(self, request, *args, **kwargs):
        """Удаляет фильм из списка пользователя 'Мои фильмы'"""
        UserFilm.objects.filter(
            user=request.user,
            film__tmdb_id=self.kwargs["tmdb_id"]
        ).delete()

        messages.info(request, "Фильм успешно удалён")
        return redirect("films:my_films")


def custom_error(request, status_code=404, exception=None):
    """Универсальная обработка всех ошибок status_code: 400, 403, 404, 500"""
    context = {
        "status_code": status_code,
        "exception": str(exception)[:100] if exception else None,
    }
    return render(request, "error_page.html", context, status=status_code)
