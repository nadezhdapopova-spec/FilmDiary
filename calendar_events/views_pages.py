from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin


class CalendarListPageView(LoginRequiredMixin, TemplateView):
    """Страница Запланированные просмотры пользователя"""
    template_name = "calendar_events/calendar_list.html"
