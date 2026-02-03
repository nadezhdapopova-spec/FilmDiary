from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.sessions.models import Session
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from calendar_events.models import CalendarEvent
from films.models import UserFilm
from reviews.models import Review
from users.models import CustomUser


class ManagerPanelView(LoginRequiredMixin, TemplateView):
    """Базовый класс для всех менеджер-панелей"""

    template_name = "users/manager/panel.html"

    def dispatch(self, request, *args, **kwargs):
        """Проверяет доступ пользователя к менеджер панели: только для менеджера и суперпользователя"""
        if not (request.user.is_superuser or request.user.groups.filter(name="Manager").exists()):
            messages.error(request, "Нет доступа к панели")
            return redirect("films:home")
        return super().dispatch(request, *args, **kwargs)


class BlockUserView(View):
    """Блокирует одного пользователя"""

    def post(self, request, user_id):
        user = get_object_or_404(CustomUser, id=user_id)

        if user == request.user:
            messages.error(request, "Нельзя заблокировать самого себя")
        elif user.is_blocked:
            messages.warning(request, f"Пользователь {user.username} уже заблокирован")
        else:
            user.is_blocked = True
            user.save()
            sessions = Session.objects.filter(expire_date__gte=timezone.now())
            for session in sessions:
                data = session.get_decoded()
                if data.get("_auth_user_id") == str(user.id):
                    session.delete()
            messages.success(request, f"Пользователь {user.username} заблокирован")
        return redirect("users:manager_users")


class UnblockUserView(ManagerPanelView, View):
    """Разблокирует одного пользователя"""

    def post(self, request, user_id):
        user = get_object_or_404(CustomUser, id=user_id)
        if not user.is_blocked:
            messages.warning(request, f"Пользователь {user.username} не заблокирован")
        else:
            user.is_blocked = False
            user.save()
            messages.success(request, f"Пользователь {user.username} разблокирован")
        return redirect("users:manager_users")


class ManagerUsersView(ManagerPanelView):
    """Менеджер панель для работы с профилями пользователей"""

    template_name = "users/manager/panel.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        status = self.request.GET.get("status", "active")

        qs = CustomUser.objects.all()

        if status == "blocked":
            qs = qs.filter(is_blocked=True)
            title = "🔒 Заблокированные пользователи"
        else:
            qs = qs.filter(is_blocked=False)
            title = "👥 Активные пользователи"

        qs = qs.annotate(
            film_count=Count("user_films"),
            review_count=Count("reviews"),
        ).order_by("-date_joined")

        context.update(
            {
                "users": qs,
                "title": title,
                "status": status,
                "total_users": qs.count(),
            }
        )

        return context


class ManagerUserDataView(ManagerPanelView):
    """Базовый класс для просмотра данных пользователя менеджером"""

    template_name = "users/manager/user_overview.html"

    def get_user(self):
        return get_object_or_404(CustomUser, id=self.kwargs["user_id"])


class ManagerUserOverviewView(ManagerUserDataView):
    """Класс для просмотра данных пользователя менеджером"""

    template_name = "users/manager/user_overview.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.get_user()
        print(f"DEBUG: user={user}, user.id={user.id if user else None}")

        context.update(
            {
                "user_obj": user,
                "user_id": self.kwargs["user_id"],
                "film_count": user.user_films.count(),
                "review_count": user.reviews.count(),
                "event_count": user.calendar_events.count(),
            }
        )
        return context


class ManagerUserFilmsView(ManagerPanelView):
    """Список фильмов пользователя"""

    template_name = "users/manager/user_data.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = get_object_or_404(CustomUser, id=self.kwargs["user_id"])

        user_films = (
            UserFilm.objects.filter(user=user)
            .select_related("film")
            .prefetch_related("film__genres", "film__actors")
            .order_by("-created_at")
        )

        context.update(
            {
                "user": user,
                "data_list": user_films,
                "total_count": user_films.count(),
                "section": "films",
                "section_title": "Фильмы",
                "empty_icon": "bi-film",
                "empty_title": "Фильмов нет",
            }
        )
        return context


class ManagerUserReviewsView(ManagerPanelView):
    """Список отзывов пользователя"""

    template_name = "users/manager/user_data.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = get_object_or_404(CustomUser, id=self.kwargs["user_id"])

        reviews = (
            Review.objects.filter(user=user)
            .select_related("film")
            .prefetch_related("film__genres")
            .order_by("-updated_at")
        )

        context.update(
            {
                "user": user,
                "data_list": reviews,
                "total_count": reviews.count(),
                "section": "reviews",
                "section_title": "Отзывы",
                "empty_icon": "bi-chat-text",
                "empty_title": "Отзывов нет",
            }
        )
        return context


class ManagerUserCalendarView(ManagerPanelView):
    """Календарь пользователя"""

    template_name = "users/manager/user_data.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = get_object_or_404(CustomUser, id=self.kwargs["user_id"])

        events = CalendarEvent.objects.filter(user=user).select_related("film").order_by("planned_date")

        context.update(
            {
                "user": user,
                "data_list": events,
                "total_count": events.count(),
                "section": "calendar",
                "section_title": "Запланировано",
                "empty_icon": "bi-calendar-x",
                "empty_title": "Планов нет",
            }
        )
        return context
