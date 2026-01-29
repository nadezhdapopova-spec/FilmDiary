from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import FormView

from users.forms.feedback_form import FeedbackForm


class FeedbackView(FormView):
    """Представление для страницы Контакты"""

    form_class = FeedbackForm
    template_name = "users/feedback.html"
    success_url = reverse_lazy("films:home")

    def form_valid(self, form):
        """Сохраняет данные формы в базу данных, добавляет 'флеш-сообщение'"""
        feedback = form.save()
        messages.success(self.request, f"Спасибо, {feedback.name}! Сообщение получено")
        return super().form_valid(form)

    def form_invalid(self, form):
        """Возвращает сообщение об ошибке, если не все поля были заполнены"""
        messages.error(self.request, "Пожалуйста, заполните все поля")
        return super().form_invalid(form)
