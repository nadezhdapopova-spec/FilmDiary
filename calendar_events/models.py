from datetime import date

from django.db import models

from django.core.exceptions import ValidationError


class CalendarEvent(models.Model):
    """Модель запланированного просмотра фильма"""
    user = models.ForeignKey(
        to="users.CustomUser",
        on_delete=models.CASCADE,
        related_name="calendar_events",
        verbose_name="Пользователь"
    )
    film = models.ForeignKey(
        to="films.Film",
        on_delete=models.CASCADE,
        related_name="calendar_events",
        verbose_name="Фильм"
    )
    planned_date = models.DateField(
        verbose_name="Дата просмотра"
    )
    note = models.TextField(
        blank=True,
        verbose_name="Комментарий"
    )
    reminder_sent = models.BooleanField(
        default=False,
        verbose_name="Отправлено"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата создания"
    )

    def clean(self):
        """Валидация поля Дата просмотра"""
        if self.planned_date and self.planned_date < date.today():
            raise ValidationError("Дата планируемого просмотра не может быть в прошлом")

    def save(self, *args, **kwargs):
        """При успешной валидации сохраняет данные в базу данных"""
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.film.title}: {self.planned_date}"

    class Meta:
        permissions = [("view_user_calendar", "Может видеть запланированные просмотры пользователей"), ]
        unique_together = ("user", "film", "planned_date")
        verbose_name = "просмотр"
        verbose_name_plural = "просмотры"
        ordering = ["-planned_date",]
        indexes = [
            models.Index(fields=["user", "film"]),
            models.Index(fields=["reminder_sent", "planned_date"]),
        ]
