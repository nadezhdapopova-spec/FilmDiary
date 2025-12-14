from celery import shared_task
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.contrib.auth import get_user_model
from config import settings


User = get_user_model()


@shared_task(bind=True, max_retries=3)
def send_activation_email_task(self, user_id, email, activation_url):
    """Асинхронная отправка письма активации аккаунта"""
    try:
        user = User.objects.get(pk=user_id)
        html_message = render_to_string(
            "users/email_activation.html",
            {"activation_url": activation_url, "user": user},
        )
        send_mail(
            subject="Подтверждение регистрации",
            message=f"Активируйте ваш аккаунт: {activation_url}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            html_message=html_message,
        )
        return "OK"

    except Exception as exc:
        raise self.retry(exc=exc, countdown=10)  # повторная попытка отправки, если SMTP упал


@shared_task(bind=True, max_retries=3)
def send_confirm_email_task(self, user_id:str, new_email:str, confirm_url: str):
    """Асинхронная отправка письма для подтверждения смены email"""
    try:
        user = User.objects.get(pk=user_id)
        html_message = render_to_string(
            "users/change_email.html",
            {
                "confirm_url": confirm_url,
                "user": user,
            },
        )
        send_mail(
            subject="Подтверждение смены email — FilmDiary",
            message=f"Подтвердите смену email: {confirm_url}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[new_email],
            html_message=html_message,
        )
        return "OK"

    except Exception as exc:
        raise self.retry(exc=exc, countdown=10)  # повторная попытка отправки, если SMTP упал
