from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.http import Http404, JsonResponse
from django.shortcuts import redirect, render
from django.views import View
from django.views.generic import ListView, TemplateView

from films.models import Film
from films.services import build_film_context, get_tmdb_movie_payload, save_film_from_tmdb, search_films


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

    model = Film
    context_object_name = "films"
    paginate_by = 12

    def get_queryset(self):
        """Возвращает список пользователя 'Мои фильмы', осуществляет поиск по q"""
        queryset = Film.objects.filter(user=self.request.user).prefetch_related("genres", "actors", "crew").order_by("-created_at")

        query = self.request.GET.get("q", "").strip()
        if query:
            queryset = queryset.filter(title__icontains=query)

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

        return context


class FilmDetailView(LoginRequiredMixin, TemplateView):
    """Представление для отображения подробной информации о фильме"""
    template_name = "films/film_detail.html"

    def get_context_data(self, **kwargs):
        """
        Возвращает карточку фильма: если фильм есть в персональной БД, берет данные из БД,
        если нет - формирует из данных сайта TMDB
        """
        context = super().get_context_data(**kwargs)
        tmdb_id = self.kwargs["tmdb_id"]

        film = (
            Film.objects.filter(tmdb_id=tmdb_id, user=self.request.user).prefetch_related("genres", "actors", "crew",).first()
        )
        if film:
            context["film"] = build_film_context(film=film)  # одинаковый context["film"] если в БД и если из TMDB
            if not context["film"]:
                raise Http404("Фильм не найден")
            return context

        payload = get_tmdb_movie_payload(tmdb_id)
        if not payload:
            raise Http404("Фильм не найден")
        context["film"] = build_film_context(
            tmdb_data=payload["details"],
            credits=payload["credits"]
        )
        if not context["film"]:
            raise Http404("Фильм не найден")
        return context


class AddFilmView(LoginRequiredMixin, View):
    """Представление для добавления фильма в список 'Мои фильмы'"""

    def post(self, request, *args, **kwargs):
        """Добавляет фильм в список пользователя 'Мои фильмы'"""
        tmdb_id = request.POST.get("tmdb_id")

        if not tmdb_id:
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({"status": "error", "message": "Нет ID фильма"}, status=400)
            else:
                messages.error(request, "Нет ID фильма")
                return redirect("films:film_search")

        film, created = save_film_from_tmdb(tmdb_id=tmdb_id, user=request.user)
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":  # AJAX ответ
            if film is None:
                return JsonResponse({"status": "error", "message": "Ошибка получения данных фильма"}, status=500)
            if created:
                return JsonResponse({"status": "added", "message": "Фильм добавлен"})
            else:
                return JsonResponse({"status": "exists", "message": "Уже в библиотеке"})
        else:  # обычный редирект
            if film:
                if created:
                    messages.success(request, "Фильм добавлен в библиотеку")
                else:
                    messages.info(request, "Фильм уже есть в библиотеке")
                return redirect("films:film_search")
            else:
                messages.error(request, "Ошибка добавления фильма")
                return redirect("films:film_search")


class UpdateFilmStatusView(LoginRequiredMixin, View):
    """Обновляет статус фильма"""
    def post(self, request, *args, **kwargs):
        film_id = request.POST.get("film_id")
        action = request.POST.get("action")  # 'plan' или 'favorite'

        try:
            film = Film.objects.get(id=film_id, user=request.user)

            if action == 'plan':
                film.is_watched = True
                film.save()
            elif action == 'favorite':
                film.is_favorite = True
                film.save()

            return JsonResponse({'status': 'success'})
        except Film.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Фильм не найден'}, status=404)


class DeleteFilmView(LoginRequiredMixin, View):
    """Представление для удаления фильма из списка'Мои фильмы'"""

    def post(self, request, *args, **kwargs):
        """Удаляет фильм из списка пользователя 'Мои фильмы'"""
        Film.objects.filter(
            user=request.user,
            tmdb_id=self.kwargs["tmdb_id"]
        ).delete()

        messages.info(request, "Фильм успешно удалён")
        return redirect("films:my_films")


def film_search_view(request):
    """Осуществляет универсальный поисковый запрос фильма: по TMDB или фильмам пользователя"""

    query = request.GET.get("q", "").strip()
    source = request.GET.get("source", "tmdb")  # 'tmdb' или 'user_films'
    params = f"&q={query}&source={source}" if query else ""
    page_number = request.GET.get("page", 1)

    results = search_films(source=source, query=query, page_num=page_number, user=request.user)

    is_user_films = source == "user_films"
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
