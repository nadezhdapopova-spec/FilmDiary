from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import models
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView

from films.models import Film
from services.permissions import can_user_view, can_user_edit, can_user_delete
from reviews.forms import ReviewForm
from reviews.models import Review


class WatchedListView(LoginRequiredMixin, ListView):
    """Представление для отображения просмотренных фильмов"""

    model = Review
    template_name = "reviews/reviews.html"
    context_object_name = "reviews"
    paginate_by = 12

    def get_context_data(self, **kwargs):
        """Добавляет поиск по отзывам в контекст"""
        context = super().get_context_data(**kwargs)
        query = self.request.GET.get("q", "").strip()

        context["search_type"] = "watched"
        context["query"] = query
        context["params"] = f"&q={query}&source=watched" if query else "&source=watched"
        context["template"] = "reviews"

        return context


    def get_queryset(self):
        """Возвращает список просмотренных фильмов пользователя"""
        queryset = (Review.objects
                    .filter(user=self.request.user)
                    .select_related("film", "user")
                    .order_by("-updated_at"))

        query = self.request.GET.get("q", "").strip()
        if query:
            queryset = queryset.filter(
                models.Q(film__title__icontains=query) |
                models.Q(user__email__icontains=query)
            )
        return queryset


class ReviewsListView(WatchedListView):
    """Представление для отображения списка отзывов на фильмы"""
    model = Review
    context_object_name = "reviews"
    template_name = "reviews/reviews.html"
    paginate_by = 12

    def get_queryset(self):
        """Возвращает список отзывов пользователя, осуществляет поиск по q"""
        queryset = (Review.objects
                    .filter(user=self.request.user)
                    .exclude(review=None)
                    .exclude(review="")
                    .exclude(review=" ")
                    .select_related("film", "user")
                    .order_by("-updated_at"))

        query = self.request.GET.get("q", "").strip()
        if query:
            queryset = queryset.filter(
                       models.Q(film__title__icontains=query) |
                       models.Q(user__email__icontains=query)
                       )

        return queryset

    def get_context_data(self, **kwargs):
        """Добавляет данные в контекст для поиска в списке отзывов на фильмы"""
        context = super().get_context_data(**kwargs)
        query = self.request.GET.get("q", "").strip()

        context["search_type"] = "reviewed"
        context["query"] = query
        context["params"] = f"&q={query}&source=reviewed" if query else "&source=reviewed"
        context["template"] = "reviews"

        return context


class ReviewDetailView(LoginRequiredMixin, DetailView):
    """Представление для отображения отзыва"""

    model = Review
    template_name = "reviews/review_detail.html"
    context_object_name = "review"

    def get_object(self, queryset=None):
        """Показывает отзыв, если пользователь имеет права на просмотр"""
        review = super().get_object(queryset)
        try:
            can_user_view(self.request.user, review)
        except (Http404, PermissionDenied):
            raise Http404("Отзыв не найден")
        return review


class ReviewCreateView(LoginRequiredMixin, CreateView):
    """Представление для создания отзыва"""

    model = Review
    form_class = ReviewForm
    template_name = "reviews/review_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.film = get_object_or_404(Film, pk=kwargs["film_id"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """Определяет в контексте объект отзыва"""
        context = super().get_context_data(**kwargs)
        context["film"] = self.film
        context["obj"] = None
        context["rating_fields"] = [
            "plot_rating",
            "acting_rating",
            "directing_rating",
            "visuals_rating",
        ]
        context["stars"] = range(1, 11)
        return context

    def form_valid(self, form):
        """Присваивает текущего авторизованного пользователя как автора отзыва"""
        form.instance.user = self.request.user
        form.instance.film = self.film

        if Review.objects.filter(user=self.request.user, film=self.film).exists():
            form.add_error(None, "Вы уже оставили отзыв на этот фильм")
            return self.form_invalid(form)

        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("reviews:review_detail", kwargs={"pk": self.object.pk})


class ReviewUpdateView(LoginRequiredMixin, UpdateView):
    """Представление для редактирования отзыва"""

    model = Review
    template_name = "reviews/review_form.html"
    form_class = ReviewForm
    context_object_name = "review"

    def get_context_data(self, **kwargs):
        """Добавляет в контекст объект отзыва"""
        context = super().get_context_data(**kwargs)
        context["obj"] = self.object
        return context

    def get_object(self, queryset=None):
        """Возвращает объект отзыва, если пользователь — автор"""
        self.object = super().get_object(queryset)
        can_user_edit(self.request.user, self.object)
        return self.object

    def get_success_url(self):
        """При успешном редактировании возвращает на страницу просмотра сообщения"""
        return reverse_lazy("reviews:review_detail", kwargs={"pk": self.object.pk})


class ReviewDeleteView(LoginRequiredMixin, DeleteView):
    """Представление для удаления отзыва"""

    model = Review
    template_name = "reviews/review_confirm_delete.html"
    context_object_name = "review"
    success_url = reverse_lazy("reviews:reviews")

    def get_object(self, queryset=None):
        """Возвращает объект отзыва, если пользователь — владелец"""
        review = super().get_object(queryset)
        can_user_delete(self.request.user, review)
        return review
