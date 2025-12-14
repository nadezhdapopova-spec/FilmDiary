from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    """Класс модели пользователя"""

    TIMEZONES = [
        ("Europe/Moscow", "Москва"),
        ("Europe/Kaliningrad", "Калининград"),
        ("Asia/Yekaterinburg", "Екатеринбург"),
        ("Asia/Novosibirsk", "Новосибирск"),
        ("Asia/Krasnoyarsk", "Красноярск"),
        ("Asia/Irkutsk", "Иркутск"),
        ("Asia/Yakutsk", "Якутск"),
        ("Asia/Vladivostok", "Владивосток"),
        ("Asia/Sakhalin", "Сахалин"),
        ("Asia/Magadan", "Магадан"),
        ("Asia/Kamchatka", "Камчатка"),
    ]

    email = models.EmailField(unique=True, verbose_name="Email")
    email_new = models.EmailField(blank=True, null=True)
    email_confirmed = models.BooleanField(default=True)
    avatar = models.ImageField(
        upload_to="users/avatars/",
        blank=True,
        null=True,
        verbose_name="Аватар",
        default="default/default.png",
        help_text="Необязательное поле",
    )
    timezone = models.CharField(max_length=32, choices=TIMEZONES, default="Europe/Moscow")
    tg_chat_id = models.BigIntegerField(blank=True, null=True, verbose_name="Telegram id")

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = [
        "username",
    ]

    def __str__(self):
        """Строковое отображение пользователя"""
        return self.username

    class Meta:
        verbose_name = "пользователь"
        verbose_name_plural = "пользователи"
        ordering = [
            "email",
        ]
