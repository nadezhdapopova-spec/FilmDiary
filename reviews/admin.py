from django.contrib import admin

from reviews.models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    """Добавляет отзывы пользователей в админ-панель"""

    list_display = ("id", "user", "film", "watched_at", "user_rating", "number_of_views", "updated_at")
    search_fields = ("id", "watched_at", "updated_at")
