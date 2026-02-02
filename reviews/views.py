import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import models
from django.db.models import OuterRef, Exists, Subquery
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy, reverse
from django.utils.timezone import now
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView


from calendar_events.models import CalendarEvent
from films.models import Film, UserFilm
from services.permissions import can_user_view, can_user_edit, can_user_delete, is_manager
from reviews.forms import ReviewForm
from reviews.models import Review


logger = logging.getLogger("filmdiary.reviews")


class BaseReviewListView(LoginRequiredMixin, ListView):
    """Базовый класс для списков просмотренных фильмов"""
    model = Review
    context_object_name = "reviews"
    paginate_by = 12

    def get_base_queryset(self):
        """Базовый queryset с annotate для карточек"""
        qs = Review.objects.select_related("film").order_by("-updated_at")
        user = self.request.user
        if not (user.is_superuser or is_manager(user)):
            qs = qs.filter(user=user)

        sort = self.request.GET.get("sort", "date")
        if sort == "rating":
            qs = qs.order_by("-user_rating", "-created_at")
        else:
            qs = qs.order_by("-created_at")

        user_films = UserFilm.objects.filter(
            user=user,
            film=OuterRef("film")
        )
        planned_events = CalendarEvent.objects.filter(
            user=user,
            film=OuterRef("film"),
            planned_date__gte=now().date()
        )

        return qs.annotate(
            user_film_id=Subquery(user_films.values("id")[:1]),
            is_favorite=Exists(user_films.filter(is_favorite=True)),
            is_planned=Exists(planned_events)
        )


class WatchedListView(BaseReviewListView):
    """Представление для отображения просмотренных=оцененных фильмов"""

    template_name = "reviews/reviews.html"


    def get_context_data(self, **kwargs):
        """Добавляет поиск по просмотренному=оцененному в контекст"""
        context = super().get_context_data(**kwargs)
        query = self.request.GET.get("q", "").strip()

        context.update({
            "search_type": "watched",
            "query": query,
            "params": f"&q={query}&source=watched" if query else "&source=watched",
            "current_sort": self.request.GET.get("sort", "date"),
            "template": "reviews",
        })
        return context


    def get_queryset(self):
        """Возвращает список просмотренных=оцененных фильмов пользователя"""
        queryset = self.get_base_queryset()

        query = self.request.GET.get("q", "").strip()
        if query:
            queryset = queryset.filter(models.Q(film__title__icontains=query))
        return queryset


class ReviewsListView(WatchedListView):
    """Представление для отображения списка текстовых отзывов на фильмы"""

    template_name = "reviews/reviews.html"

    def get_queryset(self):
        """Возвращает список отзывов пользователя, осуществляет поиск по q"""
        queryset = (self.get_base_queryset().filter(review__isnull=False)
                    .exclude(review__exact="")
                    .select_related("user"))

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

        context.update({
            "search_type": "reviewed",
            "query": query,
            "params": f"&q={query}&source=reviewed" if query else "&source=reviewed",
            "current_sort": self.request.GET.get("sort", "date"),
            "template": "reviews",
        })
        return context


class ReviewDetailView(LoginRequiredMixin, DetailView):
    """Представление для отображения карточки оцененного фильма"""

    model = Review
    template_name = "reviews/review_detail.html"
    context_object_name = "review"

    def get_object(self, queryset=None):
        """Показывает карточку оцененного фильма, если пользователь имеет права на просмотр"""
        review = super().get_object(queryset)
        can_user_view(self.request.user, review)
        return review

    def get_queryset(self):
        """Возвращает информацию о пользователе и фильме одним запросом"""
        return super().get_queryset().select_related("film", "user")


class ReviewFormContextMixin:
    rating_fields = [
        "plot_rating",
        "acting_rating",
        "directing_rating",
        "visuals_rating",
        "soundtrack_rating"
    ]
    stars = range(1, 11)

    def get_context_data(self, **kwargs):
        """Возвращает контекст для отзыва"""
        context = super().get_context_data(**kwargs)
        context["rating_fields"] = self.rating_fields
        context["stars"] = self.stars
        context["back_url"] = self.request.META.get("HTTP_REFERER", "/")
        return context


class ReviewCreateView(LoginRequiredMixin, ReviewFormContextMixin, CreateView):
    """Представление для оценки фильма и создания текстового отзыва"""

    model = Review
    form_class = ReviewForm
    template_name = "reviews/review_form.html"

    def dispatch(self, request, *args, **kwargs):
        """
        Извлекает film_id из URL, загружает объект Film из базы по pk
        и сохраняет в self.film для использования в любых методах класса
        """
        self.film = get_object_or_404(Film, tmdb_id=kwargs["tmdb_id"])

        existing_review = Review.objects.filter(user=request.user, film=self.film).first()
        if existing_review:
            return redirect("reviews:review_detail", pk=existing_review.pk)

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """Добавляет данные в контекст"""
        context = super().get_context_data(**kwargs)
        context["film"] = self.film
        context["obj"] = None
        return context

    def form_valid(self, form):
        """Присваивает текущего авторизованного пользователя как автора отзыва"""
        form.instance.user = self.request.user
        form.instance.film = self.film

        if Review.objects.filter(user=self.request.user, film=self.film).exists():
            logger.warning("ReviewCreate DUP: user=%s film=%s",
                           self.request.user.id, self.film.tmdb_id)
            form.add_error(None, "Вы уже оставили отзыв на этот фильм")
            return self.form_invalid(form)

        review = super().form_valid(form)
        logger.info("ReviewCreate OK: user=%s film=%s", self.request.user.id, self.film.tmdb_id)
        return review

    def form_invalid(self, form):
        """Валидация формы создания отзыва: неуспешная валидация"""
        logger.warning("ReviewCreate FAIL: user=%s film=%s errors=%s",
                       self.request.user.id, self.film.tmdb_id, form.errors)
        print(form.errors)
        return super().form_invalid(form)

    def get_success_url(self):
        """При успешном сохнанении перенаправляет на страницу Мои фильмы"""
        return reverse("films:my_films")


class ReviewUpdateView(LoginRequiredMixin, ReviewFormContextMixin, UpdateView):
    """Представление для редактирования отзыва"""

    model = Review
    template_name = "reviews/review_form.html"
    form_class = ReviewForm
    context_object_name = "review"

    def get_object(self, queryset=None):
        """Возвращает объект отзыва с данными о фильме, если пользователь — автор"""
        self.object = super().get_object(queryset)
        can_user_edit(self.request.user, self.object)
        self.film = self.object.film
        return self.object

    def form_valid(self, form):
        """Валидация формы редактирования отзыва: успешная валидация"""
        review = super().form_valid(form)
        logger.info("ReviewUpdate OK: review=%s user=%s",
                    self.object.pk, self.request.user.id)
        return review

    def form_invalid(self, form):
        """Валидация формы редактирования отзыва: неуспешная валидация"""
        logger.warning("ReviewUpdate FAIL: review=%s errors=%s",
                       self.object.pk, form.errors)
        return super().form_invalid(form)

    def get_form_kwargs(self):
        """Передает корректный initial из Review в форму при редактировании - для отображения даты и просмотров"""
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.object
        return kwargs

    def get_queryset(self):
        """Возвращает информацию о пользователе и фильме одним запросом"""
        return super().get_queryset().select_related("film", "user")

    def get_context_data(self, **kwargs):
        """Добавляет в контекст объект отзыва"""
        context = super().get_context_data(**kwargs)
        context["obj"] = self.object
        context["film"] = self.film
        return context

    def get_success_url(self):
        """При успешном редактировании возвращает на страницу Мои фильмы"""
        return reverse("films:my_films")

class ReviewDeleteView(LoginRequiredMixin, DeleteView):
    """Представление для удаления фильма из промотренных=оцененных"""

    model = Review
    context_object_name = "review"
    success_url = reverse_lazy("reviews:reviews")

    def get_object(self, queryset=None):
        """Возвращает объект отзыва, если пользователь — владелец"""
        review = super().get_object(queryset)
        can_user_delete(self.request.user, review)
        return review
