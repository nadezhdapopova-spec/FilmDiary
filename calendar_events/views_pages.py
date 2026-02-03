from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class CalendarListPageView(LoginRequiredMixin, TemplateView):
    """Страница Запланированные просмотры пользователя"""

    template_name = "calendar_events/calendar_list.html"
