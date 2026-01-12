from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView

from common.permissions import can_user_view, can_user_edit, can_user_delete
from reviews.forms import ReviewForm
from reviews.models import Review


class ReviewsListView(LoginRequiredMixin, ListView):
    """Представление для отображения списка отзывов на фильм"""

    model = Review
    template_name = "reviews/reviews.html"
    context_object_name = "reviews"
    paginate_by = 10

    def get_context_data(self, **kwargs):
        """Добавляет поиск по отзывам в контекст"""
        context = super().get_context_data(**kwargs)
        query = self.request.GET.get("q", "").strip()

        context["search_type"] = "reviews"
        context["query"] = query
        context["params"] = f"&q={query}&source=reviews" if query else "&source=reviews"
        # context["view_url"] = "films:my_films"
        # context["template"] = "my_films"

        return context

    def get_queryset(self):
        """Возвращает список отзывов пользователя на фильмы"""
        queryset = Review.objects.filter(user=self.request.user).select_related("film").order_by("-updated_at")

        query = self.request.GET.get("q", "").strip()
        if query:
            queryset = queryset.filter(title__icontains=query)

        return queryset


class ReviewDetailView(LoginRequiredMixin, DetailView):
    """Представление для отображения отзыва"""

    model = Review
    template_name = "reviews/review_detail.html"
    context_object_name = "review"

    def get_object(self, queryset=None):
        """Показывает отзыв, если пользователь имеет права на просмотр"""
        review = super().get_object(queryset)
        can_user_view(self.request.user, review)
        if not review:
            raise Http404("Отзыв не найден")
        return review


class ReviewCreateView(LoginRequiredMixin, CreateView):
    """Представление для создания отзыва"""

    model = Review
    form_class = ReviewForm
    template_name = "reviews/review_form.html"
    context_object_name = "review"
    success_url = reverse_lazy("reviews:reviews")

    def get_context_data(self, **kwargs):
        """Определяет в контексте объект отзыва"""
        context = super().get_context_data(**kwargs)
        context["obj"] = None
        return context

    def form_valid(self, form):
        """Присваивает текущего авторизованного пользователя как автора отзыва"""
        form.instance.user = self.request.user
        response = super().form_valid(form)
        return response


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
