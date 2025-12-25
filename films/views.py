from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.shortcuts import redirect, render
from django.views import View
from django.views.generic import ListView, TemplateView

from films.models import Film
from films.services import build_film_context, get_tmdb_movie_payload, save_film_from_tmdb


class HomeView(View):
    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return render(request, "films/home.html")
        context = {
            # "recs_for_me": get_recommendations(request.user, limit=4),
            # "planned_movies": get_planned(request.user, limit=4),
            # "recent_movies": get_recent(request.user, limit=4),
        }
        return render(request, "films/home.html", context)


class UserListFilmView(LoginRequiredMixin, ListView):
    """Представление для отображения списка 'Мои фильмы'"""

    model = Film
    context_object_name = "films"
    paginate_by = 12

    def get_queryset(self):
        """Возвращает список пользователя 'Мои фильмы'"""
        return Film.objects.filter(
            user=self.request.user
        ).select_related(
            "director"
        ).prefetch_related(
            "genres", "actors"
        )


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
            Film.objects.filter(tmdb_id=tmdb_id, user=self.request.user).select_related()
            .prefetch_related("genres","filmactor_set__actor","filmcrew_set__person",).first()
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

        film, created = save_film_from_tmdb(tmdb_id=tmdb_id, user=request.user)
        if created:
            messages.success(request, "Фильм добавлен в библиотеку")
        else:
            messages.info(request, "Фильм уже есть в библиотеке")

        return redirect("films:film_detail", tmdb_id=tmdb_id)


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
