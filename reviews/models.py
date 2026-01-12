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
    user_rating = models.FloatField(verbose_name="Оценка")
    review = models.TextField(blank=True, verbose_name="Отзыв")
    number_of_views = models.PositiveIntegerField(null=True, blank=True, verbose_name="Просмотров")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")


    def __str__(self):
        return f"{self.user.username} - {self.film.title} ({self.user_rating})"

    class Meta:
        unique_together = ("user", "film")
        verbose_name = "отзыв"
        verbose_name_plural = "отзывы"
        ordering = ["-updated_at",]
        indexes = [
            models.Index(fields=["user", "film"]),
            models.Index(fields=["-updated_at"]),
        ]
