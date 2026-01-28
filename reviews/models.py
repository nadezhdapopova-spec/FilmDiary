from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models


class Review(models.Model):
    """Класс модели отзыва на фильм"""
    user = models.ForeignKey(
        to="users.CustomUser",
        on_delete=models.CASCADE,
        related_name="reviews",
        verbose_name="Пользователь")
    film = models.ForeignKey(
        to="films.Film",
        on_delete=models.CASCADE,
        related_name="reviews",
        verbose_name="Фильм")
    watched_at = models.DateField(verbose_name="Дата просмотра")
    plot_rating = models.FloatField(
        verbose_name="Сюжет",
        validators=[MinValueValidator(1), MaxValueValidator(10)]
    )
    acting_rating = models.FloatField(
        verbose_name="Актеры",
        validators=[MinValueValidator(1), MaxValueValidator(10)]
    )
    directing_rating = models.FloatField(
        verbose_name="Режиссура",
        validators=[MinValueValidator(1), MaxValueValidator(10)]
    )
    visuals_rating = models.FloatField(
        verbose_name="Визуал",
        validators=[MinValueValidator(1), MaxValueValidator(10)]
    )
    soundtrack_rating = models.FloatField(
        verbose_name="Саундтрек",
        validators=[MinValueValidator(1), MaxValueValidator(10)]
    )
    user_rating = models.FloatField(verbose_name="Оценка")
    review = models.TextField(blank=True, verbose_name="Отзыв")
    number_of_views = models.PositiveIntegerField(null=True, blank=True, verbose_name="Просмотров")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    def calculate_rating(self):
        """Вычисляет среднее 5 критериев оценки фильма"""
        return (
                self.plot_rating +
                self.acting_rating +
                self.directing_rating +
                self.visuals_rating +
                self.soundtrack_rating
        ) / 5

    def save(self, *args, **kwargs):
        """Сохраняет среднее 5 критериев оценки фильма как общий пользовательский рейтинг фильма"""
        self.user_rating = self.calculate_rating()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} - {self.film.title} ({self.user_rating})"

    class Meta:
        permissions = [("view_user_reviews", "Может просматривать оценки и отзывы пользователей на фильмы"), ]
        unique_together = ("user", "film")
        verbose_name = "отзыв"
        verbose_name_plural = "отзывы"
        ordering = ["-updated_at",]
        indexes = [
            models.Index(fields=["user", "film"]),
            models.Index(fields=["-updated_at"]),
        ]
